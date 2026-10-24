// SPDX-License-Identifier: GPL-3.0-only
#include "SeqBridge.h"
#include <algorithm>
#include <cstring>

namespace lynn
{
SeqBridge::SeqBridge() {}
SeqBridge::~SeqBridge() { if (scratch) lxrseq_destroy (scratch); }

std::array<bool, kSteps> SeqBridge::euclidPreview (int length, int steps, int rotation)
{
    std::array<bool, kSteps> out {};
    length = std::clamp (length, 1, 64); steps = std::clamp (steps, 1, length); rotation = std::clamp (rotation, 0, length - 1);
    if (!scratch) { LxrSeqSink sink {}; static const std::uint8_t zeros[256] = {}; sink.originalCc = zeros; scratch = lxrseq_create (&sink, 1); }
    lxrseq_euclid_length (scratch, 0, (unsigned) length);
    lxrseq_euclid_steps (scratch, 0, (unsigned) steps, 0);
    lxrseq_euclid_rotation (scratch, 0, (unsigned) rotation, 0);
    std::uint16_t m[4]; unsigned len = 0;
    lxrseq_get_main_steps (scratch, 0, 0, m, &len);
    for (int i = 0; i < length; ++i) out[(size_t) i] = ((m[i / 16] >> (i % 16)) & 1) != 0;
    return out;
}                                   // empty = what a fresh sequencer holds, so mirror and engine start in sync

void SeqBridge::loadDemo()
{
    bank[0] = UiPattern();
    auto on = [this] (int t, int s, int v) { bank[0].tracks[(size_t) t].on[(size_t) s] = 1; bank[0].tracks[(size_t) t].vol[(size_t) s] = (std::uint8_t) v; };
    for (int s : { 0, 4, 8, 12 }) on (0, s, 110);
    for (int s : { 4, 12 }) on (3, s, 105);
    for (int s = 0; s < 16; s += 2) on (5, s, s % 4 ? 70 : 95);
    on (6, 14, 90);
}

// ---- queue --------------------------------------------------------------------------------------------------------------
void SeqBridge::push (const SeqCommand& c)
{
    if (!pending.empty()) { pending.push_back (c); flush(); return; }
    const size_t h = head.load (std::memory_order_relaxed);
    if (h - tail.load (std::memory_order_acquire) >= kQueue) { pending.push_back (c); return; }
    ring[h & (kQueue - 1)] = c;
    head.store (h + 1, std::memory_order_release);
}

void SeqBridge::flush()
{
    while (!pending.empty())
    {
        const size_t h = head.load (std::memory_order_relaxed);
        if (h - tail.load (std::memory_order_acquire) >= kQueue) return;
        ring[h & (kQueue - 1)] = pending.front();
        head.store (h + 1, std::memory_order_release);
        pending.pop_front();
    }
}

void SeqBridge::editStep (int p, int t, int i)
{
    const auto& tr = bank[(size_t) p].tracks[(size_t) t]; const size_t k = (size_t) i;
    SeqCommand c; c.type = SeqCommand::Step; c.pat = (std::uint8_t) p; c.track = (std::uint8_t) t; c.idx = (std::uint8_t) i;
    c.on = tr.on[k]; c.vol = tr.vol[k]; c.prob = tr.prob[k]; c.note = tr.note[k]; c.flam = tr.flam[k]; c.shift = tr.shift[k];
    c.lp1 = tr.lockPar1[k]; c.lv1 = tr.lockVal1[k]; c.lp2 = tr.lockPar2[k]; c.lv2 = tr.lockVal2[k];
    push (c);
}
void SeqBridge::editLength (int p, int t) { SeqCommand c; c.type = SeqCommand::Length; c.pat = (std::uint8_t) p; c.track = (std::uint8_t) t; c.value = bank[(size_t) p].tracks[(size_t) t].length; push (c); }
void SeqBridge::editMute (int t) { SeqCommand c; c.type = SeqCommand::Mute; c.track = (std::uint8_t) t; c.value = audible (t) ? 0 : 1; push (c); }
void SeqBridge::editShuffle (int p) { SeqCommand c; c.type = SeqCommand::Shuffle; c.pat = (std::uint8_t) p; c.value = bank[(size_t) p].shuffle; push (c); }
void SeqBridge::audition (int t, int vel)
{
    if (t < 0 || t >= kTracks) return;
    SeqCommand c; c.type = SeqCommand::Audition; c.track = (std::uint8_t) t; c.vol = (std::uint8_t) std::clamp (vel, 1, 127); push (c);
}

void SeqBridge::sendPattern (int p, const UiPattern* old)
{
    const auto& n = bank[(size_t) p];
    for (int t = 0; t < kTracks; ++t)
    {
        const auto& a = n.tracks[(size_t) t];
        if (!old || old->tracks[(size_t) t].length != a.length) editLength (p, t);
        for (int i = 0; i < kSteps; ++i)
        {
            const size_t k = (size_t) i;
            if (old)
            {
                const auto& b = old->tracks[(size_t) t];
                if (a.on[k] == b.on[k] && a.vol[k] == b.vol[k] && a.prob[k] == b.prob[k] && a.note[k] == b.note[k] && a.flam[k] == b.flam[k] && a.shift[k] == b.shift[k]
                    && a.lockPar1[k] == b.lockPar1[k] && a.lockVal1[k] == b.lockVal1[k] && a.lockPar2[k] == b.lockPar2[k] && a.lockVal2[k] == b.lockVal2[k]) continue;
            }
            editStep (p, t, i);
        }
    }
    if (!old || old->shuffle != n.shuffle) editShuffle (p);
}

void SeqBridge::sendSong()
{
    SeqCommand m; m.type = SeqCommand::SongMode; m.value = song.enabled ? 1 : 0; push (m);
    for (int i = 0; i < kSongLength; ++i) { SeqCommand c; c.type = SeqCommand::SongEntry; c.idx = (std::uint8_t) i; c.value = song.entries[(size_t) i]; push (c); }
}

void SeqBridge::setPattern (int p, const UiPattern& np)
{
    const UiPattern old = bank[(size_t) p];
    bank[(size_t) p] = np;
    sendPattern (p, &old);
}

void SeqBridge::setBank (const std::array<UiPattern, kPatterns>& nb, const UiSong& ns, std::uint8_t newMutes)
{
    for (int p = 0; p < kPatterns; ++p)
        if (!(bank[(size_t) p] == nb[(size_t) p])) { const UiPattern old = bank[(size_t) p]; bank[(size_t) p] = nb[(size_t) p]; sendPattern (p, &old); }
    if (!(song == ns)) { song = ns; sendSong(); }
    for (int t = 0; t < kTracks; ++t) if (((mutes ^ newMutes) >> t) & 1) { mutes = (std::uint8_t) ((mutes & ~(1 << t)) | (newMutes & (1 << t))); editMute (t); }
}

// ---- UI commands --------------------------------------------------------------------------------------------------------
bool SeqBridge::applyUiCommand (const std::vector<double>& a, const std::string& n)
{
    edits.fetch_add (1, std::memory_order_relaxed);
    auto at = [&] (size_t k, int lo, int hi) { return a.size() > k && a[k] >= lo && a[k] <= hi ? (int) a[k] : -1; };
    auto val = [&] (size_t k, int lo, int hi) { return (std::uint8_t) std::clamp (a.size() > k ? (int) a[k] : lo, lo, hi); };
    const int p = at (0, 0, kPatterns - 1);

    if (n == "step" || n == "stepVol" || n == "stepProb" || n == "stepNote" || n == "stepFlam" || n == "stepShift")
    {
        const int t = at (1, 0, kTracks - 1), i = at (2, 0, kSteps - 1); if (p < 0 || t < 0 || i < 0) return false;
        auto& tr = bank[(size_t) p].tracks[(size_t) t]; const size_t k = (size_t) i;
        if (n == "step")
        {
            tr.on[k] = a.size() > 3 && a[3] != 0;
            if (tr.on[k]) { if (!tr.vol[k]) tr.vol[k] = 100; if (!tr.prob[k]) tr.prob[k] = 100; }
        }
        else if (n == "stepVol") tr.vol[k] = val (3, 1, 127);
        else if (n == "stepProb") tr.prob[k] = val (3, 1, 100);
        else if (n == "stepNote") tr.note[k] = val (3, 0, 127);
        else if (n == "stepFlam") tr.flam[k] = val (3, 0, 5);
        else tr.shift[k] = val (3, 0, 14);
        editStep (p, t, i); return true;
    }
    if (n == "stepLock")                                         // [pat, track, step, slot 1|2, par (-1 = none), value]
    {
        const int t = at (1, 0, kTracks - 1), i = at (2, 0, kSteps - 1), slot = at (3, 1, 2); if (p < 0 || t < 0 || i < 0 || slot < 0) return false;
        const bool none = a.size() > 4 && a[4] < 0;
        if (!none && at (4, 0, kMaxLockPar) < 0) return false;
        auto& tr = bank[(size_t) p].tracks[(size_t) t]; const size_t k = (size_t) i;
        auto& par = slot == 1 ? tr.lockPar1 : tr.lockPar2; auto& vl = slot == 1 ? tr.lockVal1 : tr.lockVal2;
        par[k] = none ? kNoLock : (std::uint8_t) a[4]; vl[k] = val (5, 0, 127);
        editStep (p, t, i); return true;
    }
    if (n == "trackLength") { const int t = at (1, 0, kTracks - 1); if (p < 0 || t < 0) return false; bank[(size_t) p].tracks[(size_t) t].length = val (2, 1, 64); editLength (p, t); return true; }
    if (n == "shuffle") { if (p < 0) return false; bank[(size_t) p].shuffle = val (1, 0, 127); editShuffle (p); return true; }
    if (n == "solo") { const int t = at (0, 0, kTracks - 1); if (t < 0) return false; const std::uint8_t before = solos; solos = (std::uint8_t) ((solos & ~(1 << t)) | ((a.size() > 1 && a[1] != 0) ? (1 << t) : 0));
                       if (before != solos) for (int i = 0; i < kTracks; ++i) editMute (i);       // solo changes every track's effective mute
                       return true; }
    if (n == "mute") { const int t = at (0, 0, kTracks - 1); if (t < 0) return false; mutes = (std::uint8_t) ((mutes & ~(1 << t)) | ((a.size() > 1 && a[1] != 0) ? (1 << t) : 0)); editMute (t); return true; }
    if (n == "clearTrack")
    {
        const int t = at (1, 0, kTracks - 1); if (p < 0 || t < 0) return false;
        const UiPattern old = bank[(size_t) p]; const auto len = old.tracks[(size_t) t].length;
        bank[(size_t) p].tracks[(size_t) t] = UiTrack(); bank[(size_t) p].tracks[(size_t) t].length = len;
        sendPattern (p, &old); return true;
    }
    if (n == "copyTrack")
    {
        const int s = at (1, 0, kTracks - 1), d = at (2, 0, kTracks - 1); if (p < 0 || s < 0 || d < 0) return false;
        const UiPattern old = bank[(size_t) p]; bank[(size_t) p].tracks[(size_t) d] = bank[(size_t) p].tracks[(size_t) s];
        sendPattern (p, &old); return true;
    }
    if (n == "euclid")                                             // [pat, track, length, steps, rotation]: replaces the track's steps
    {
        const int t = at (1, 0, kTracks - 1), len = at (2, 1, 64), st = at (3, 1, 64), rot = at (4, 0, 63); if (p < 0 || t < 0 || len < 0 || st < 0 || rot < 0) return false;
        const auto bits = euclidPreview (len, st, rot);
        const UiPattern old = bank[(size_t) p]; auto& tr = bank[(size_t) p].tracks[(size_t) t];
        tr.length = (std::uint8_t) len;
        for (int i = 0; i < kSteps; ++i) { tr.on[(size_t) i] = bits[(size_t) i] ? 1 : 0; if (bits[(size_t) i] && !old.tracks[(size_t) t].on[(size_t) i]) { tr.vol[(size_t) i] = 100; } }
        sendPattern (p, &old); return true;
    }
    if (n == "roll") { const int t = at (0, 0, kTracks - 1); if (t < 0) return false; SeqCommand c; c.type = SeqCommand::Roll; c.track = (std::uint8_t) t; c.value = a.size() > 1 && a[1] != 0; push (c); return true; }
    if (n == "rollRate") { const int r = at (0, 0, 5); if (r < 0) return false; SeqCommand c; c.type = SeqCommand::RollRate; c.value = (std::uint16_t) r; push (c); return true; }
    if (n == "clearPattern") { if (p < 0) return false; setPattern (p, UiPattern()); return true; }
    if (n == "copyPattern") { const int s = at (0, 0, kPatterns - 1), d = at (1, 0, kPatterns - 1); if (s < 0 || d < 0) return false; setPattern (d, bank[(size_t) s]); return true; }
    if (n == "selectPattern") { if (p < 0) return false; SeqCommand c; c.type = SeqCommand::SelectPattern; c.pat = (std::uint8_t) p; push (c); return true; }
    if (n == "songMode") { song.enabled = a.size() > 0 && a[0] != 0; SeqCommand c; c.type = SeqCommand::SongMode; c.value = song.enabled ? 1 : 0; push (c); return true; }
    if (n == "songSet")
    {
        const int pos = at (0, 0, kSongLength - 1), v = at (1, 0, kSongLoop); if (pos < 0 || v < 0) return false;
        song.entries[(size_t) pos] = (std::uint8_t) v;
        SeqCommand c; c.type = SeqCommand::SongEntry; c.idx = (std::uint8_t) pos; c.value = (std::uint16_t) v; push (c); return true;
    }
    return false;
}

// ---- state ----------------------------------------------------------------------------------------------------------------
std::string SeqBridge::serialize() const
{
    std::string s; s.push_back (3); s.push_back (song.enabled ? 1 : 0); s.push_back ((char) mutes);
    for (auto v : song.entries) s.push_back ((char) v);
    int count = 0; for (int p = 0; p < kPatterns; ++p) if (used (p)) ++count;
    s.push_back ((char) count);
    for (int p = 0; p < kPatterns; ++p)
    {
        if (!used (p)) continue;
        const auto& pt = bank[(size_t) p];
        s.push_back ((char) p); s.push_back ((char) pt.shuffle);
        for (const auto& t : pt.tracks)
        {
            s.push_back ((char) t.length);
            for (int i = 0; i < kSteps; ++i) { const size_t k = (size_t) i; for (std::uint8_t v : { t.on[k], t.vol[k], t.prob[k], t.note[k], t.flam[k], t.shift[k], t.lockPar1[k], t.lockVal1[k], t.lockPar2[k], t.lockVal2[k] }) s.push_back ((char) v); }
        }
    }
    return s;
}

bool SeqBridge::deserialize (const std::uint8_t* d, size_t n)
{
    const bool v3 = n >= 1 && d[0] == 3;
    auto readTrack = [v3] (UiTrack& t, const std::uint8_t* d, size_t& o)
    {
        t.length = std::clamp<std::uint8_t> (d[o++], 1, 64);
        for (int i = 0; i < kSteps; ++i)
        {
            const size_t k = (size_t) i;
            t.on[k] = d[o++] ? 1 : 0; t.vol[k] = std::clamp<std::uint8_t> (d[o++], 1, 127); t.prob[k] = std::clamp<std::uint8_t> (d[o++], 1, 100);
            t.note[k] = std::min<std::uint8_t> (d[o++], 127); t.flam[k] = std::min<std::uint8_t> (d[o++], 5); t.shift[k] = std::min<std::uint8_t> (d[o++], 14);
            if (v3)
            {
                const std::uint8_t p1 = d[o++], v1 = d[o++], p2 = d[o++], v2 = d[o++];
                t.lockPar1[k] = p1 <= kMaxLockPar ? p1 : kNoLock; t.lockVal1[k] = std::min<std::uint8_t> (v1, 127);
                t.lockPar2[k] = p2 <= kMaxLockPar ? p2 : kNoLock; t.lockVal2[k] = std::min<std::uint8_t> (v2, 127);
            }
        }
    };
    std::array<UiPattern, kPatterns> nb; UiSong ns; std::uint8_t nm = 0;
    if (n >= 1 && d[0] == 1 && n == 2 + (size_t) kTracks * (2 + kSteps * 6))          // schema 1: one pattern, mute flag per track
    {
        nb[0].shuffle = std::min<std::uint8_t> (d[1], 127); size_t o = 2;
        for (int t = 0; t < kTracks; ++t)
        {
            auto& tr = nb[0].tracks[(size_t) t];
            tr.length = std::clamp<std::uint8_t> (d[o++], 1, 64);
            if (d[o++]) nm |= (std::uint8_t) (1 << t);
            for (int i = 0; i < kSteps; ++i)
            {
                const size_t k = (size_t) i;
                tr.on[k] = d[o++] ? 1 : 0; tr.vol[k] = std::clamp<std::uint8_t> (d[o++], 1, 127); tr.prob[k] = std::clamp<std::uint8_t> (d[o++], 1, 100);
                tr.note[k] = std::min<std::uint8_t> (d[o++], 127); tr.flam[k] = std::min<std::uint8_t> (d[o++], 5); tr.shift[k] = std::min<std::uint8_t> (d[o++], 14);
            }
        }
        setBank (nb, ns, nm); return true;
    }
    if (n < 4 + (size_t) kSongLength || (d[0] != 2 && d[0] != 3)) return false;
    ns.enabled = d[1] != 0; nm = d[2] & 0x7f;
    size_t o = 3; for (auto& e : ns.entries) e = std::min<std::uint8_t> (d[o++], kSongLoop);
    const int count = d[o++];
    const size_t per = 2 + (size_t) kTracks * (1 + kSteps * (v3 ? 10 : 6));
    if (count > kPatterns || n != o + (size_t) count * per) return false;
    for (int c = 0; c < count; ++c)
    {
        const int p = d[o++]; if (p >= kPatterns) return false;
        nb[(size_t) p].shuffle = std::min<std::uint8_t> (d[o++], 127);
        for (auto& t : nb[(size_t) p].tracks) readTrack (t, d, o);
    }
    setBank (nb, ns, nm);
    return true;
}

// ---- audio thread ---------------------------------------------------------------------------------------------------------------
void SeqBridge::drain (EngineHost& host) noexcept
{
    LxrSeq* q = host.sequencer();
    size_t t = tail.load (std::memory_order_relaxed);
    const size_t h = head.load (std::memory_order_acquire);
    for (; t != h; ++t)
    {
        const SeqCommand& c = ring[t & (kQueue - 1)];
        switch (c.type)
        {
            case SeqCommand::Step:
                lxrseq_set_main_step (q, c.pat, c.track, c.idx, c.on);
                lxrseq_set_step (q, c.pat, c.track, c.idx, c.vol, c.prob, c.note);
                lxrseq_set_step_timing (q, c.pat, c.track, c.idx, c.flam, c.shift);
                lxrseq_set_plock (q, c.pat, c.track, c.idx, 1, c.lp1 == kNoLock ? 0xff : (c.lp1 < 127 ? c.lp1 + 1u : c.lp1), c.lv1);
                lxrseq_set_plock (q, c.pat, c.track, c.idx, 2, c.lp2 == kNoLock ? 0xff : (c.lp2 < 127 ? c.lp2 + 1u : c.lp2), c.lv2);
                break;
            case SeqCommand::Length:  lxrseq_set_track_length (q, c.pat, c.track, c.value); break;
            case SeqCommand::Mute:    lxrseq_set_mute (q, c.track, c.value); break;
            case SeqCommand::Shuffle: lxrseq_set_pattern_shuffle (q, c.pat, c.value); break;
            case SeqCommand::Audition: lxr_trigger (host.raw(), c.track, 60, c.vol); break;
            case SeqCommand::SelectPattern: lxrseq_set_next_pattern (q, c.pat); break;
            case SeqCommand::SongMode: lxrseq_set_song_mode (q, c.value); break;
            case SeqCommand::SongEntry: lxrseq_set_song_entry (q, c.idx, c.value); break;
            case SeqCommand::Roll: lxrseq_set_roll (q, c.track, c.value); break;
            case SeqCommand::RollRate: lxrseq_set_roll_rate (q, c.value); break;
        }
    }
    tail.store (t, std::memory_order_release);
}

void SeqBridge::publishPlayhead (EngineHost& host, double bpm, float pl, float pr) noexcept
{
    if (pl > peakL.load (std::memory_order_relaxed)) peakL.store (pl, std::memory_order_relaxed);
    if (pr > peakR.load (std::memory_order_relaxed)) peakR.store (pr, std::memory_order_relaxed);
    std::uint64_t w = 0;
    for (int t = 0; t < kTracks; ++t) { const int s = lxrseq_step_index (host.sequencer(), (unsigned) t); w |= (std::uint64_t) (s < 0 ? 0 : s & 0xff) << (8 * t); }
    if (lxrseq_is_running (host.sequencer())) w |= (std::uint64_t) 1 << 56;
    playheadWord.store (w, std::memory_order_relaxed);
    patternWord.store ((std::uint32_t) (lxrseq_active_pattern (host.sequencer()) & 0xff) | (std::uint32_t) (lxrseq_pending_pattern (host.sequencer()) & 0xff) << 8
                       | (std::uint32_t) (lxrseq_song_position (host.sequencer()) & 0xff) << 16, std::memory_order_relaxed);
    bpmShown.store ((float) bpm, std::memory_order_relaxed);
}

SeqBridge::Level SeqBridge::readLevel() noexcept { return { peakL.exchange (0.f, std::memory_order_relaxed), peakR.exchange (0.f, std::memory_order_relaxed) }; }

SeqBridge::Playhead SeqBridge::readPlayhead() const noexcept
{
    const auto w = playheadWord.load (std::memory_order_relaxed);
    const auto pw = patternWord.load (std::memory_order_relaxed);
    Playhead p { ((w >> 56) & 1) != 0, {}, (double) bpmShown.load (std::memory_order_relaxed), (int) (pw & 0xff), (int) ((pw >> 8) & 0xff), (int) ((pw >> 16) & 0xff) };
    for (int t = 0; t < kTracks; ++t) p.steps[(size_t) t] = (int) ((w >> (8 * t)) & 0xff);
    return p;
}
} // namespace lynn
