// SPDX-License-Identifier: GPL-3.0-only
#include "SeqBridge.h"
#include <algorithm>
#include <cstring>

namespace lynn
{
SeqBridge::SeqBridge() { loadDemo(); }

void SeqBridge::loadDemo()
{
    mirror = UiPattern();
    auto on = [this] (int t, int s, int v) { mirror.tracks[(size_t) t].on[(size_t) s] = 1; mirror.tracks[(size_t) t].vol[(size_t) s] = (std::uint8_t) v; };
    for (int s : { 0, 4, 8, 12 }) on (0, s, 110);
    for (int s : { 4, 12 }) on (3, s, 105);
    for (int s = 0; s < 16; s += 2) on (5, s, s % 4 ? 70 : 95);
    on (6, 14, 90);
}

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

void SeqBridge::editStep (int t, int i)
{
    const auto& tr = mirror.tracks[(size_t) t]; const size_t k = (size_t) i;
    SeqCommand c; c.type = SeqCommand::Step; c.track = (std::uint8_t) t; c.idx = (std::uint8_t) i;
    c.on = tr.on[k]; c.vol = tr.vol[k]; c.prob = tr.prob[k]; c.note = tr.note[k]; c.flam = tr.flam[k]; c.shift = tr.shift[k];
    push (c);
}
void SeqBridge::editLength (int t) { SeqCommand c; c.type = SeqCommand::Length; c.track = (std::uint8_t) t; c.value = mirror.tracks[(size_t) t].length; push (c); }
void SeqBridge::editMute (int t) { SeqCommand c; c.type = SeqCommand::Mute; c.track = (std::uint8_t) t; c.value = mirror.tracks[(size_t) t].muted ? 1 : 0; push (c); }
void SeqBridge::audition (int t, int vel)
{
    if (t < 0 || t >= kTracks) return;
    SeqCommand c; c.type = SeqCommand::Audition; c.track = (std::uint8_t) t; c.vol = (std::uint8_t) std::clamp (vel, 1, 127); push (c);
}

void SeqBridge::editShuffle() { SeqCommand c; c.type = SeqCommand::Shuffle; c.value = mirror.shuffle; push (c); }

void SeqBridge::setPattern (const UiPattern& p) { mirror = p; resyncAll(); }

void SeqBridge::resyncAll()
{
    for (int t = 0; t < kTracks; ++t)
    {
        editLength (t); editMute (t);
        for (int i = 0; i < kSteps; ++i) editStep (t, i);
    }
    editShuffle();
}

bool SeqBridge::applyUiCommand (const std::vector<double>& a, const std::string& n)
{
    edits.fetch_add (1, std::memory_order_relaxed);
    auto track = [&] (size_t k) { return a.size() > k && a[k] >= 0 && a[k] < kTracks ? (int) a[k] : -1; };
    auto step = [&] (size_t k) { return a.size() > k && a[k] >= 0 && a[k] < kSteps ? (int) a[k] : -1; };
    auto val = [&] (size_t k, int lo, int hi) { return (std::uint8_t) std::clamp (a.size() > k ? (int) a[k] : lo, lo, hi); };
    if (n == "step" || n == "stepVol" || n == "stepProb" || n == "stepNote" || n == "stepFlam" || n == "stepShift")
    {
        const int t = track (0), i = step (1); if (t < 0 || i < 0) return false;
        auto& tr = mirror.tracks[(size_t) t]; const size_t k = (size_t) i;
        if (n == "step")
        {
            tr.on[k] = a.size() > 2 && a[2] != 0;
            if (tr.on[k]) { if (!tr.vol[k]) tr.vol[k] = 100; if (!tr.prob[k]) tr.prob[k] = 100; }
        }
        else if (n == "stepVol") tr.vol[k] = val (2, 1, 127);
        else if (n == "stepProb") tr.prob[k] = val (2, 1, 100);
        else if (n == "stepNote") tr.note[k] = val (2, 0, 127);
        else if (n == "stepFlam") tr.flam[k] = val (2, 0, 5);
        else tr.shift[k] = val (2, 0, 14);
        editStep (t, i); return true;
    }
    if (n == "trackLength") { const int t = track (0); if (t < 0) return false; mirror.tracks[(size_t) t].length = val (1, 1, 64); editLength (t); return true; }
    if (n == "mute") { const int t = track (0); if (t < 0) return false; mirror.tracks[(size_t) t].muted = a.size() > 1 && a[1] != 0; editMute (t); return true; }
    if (n == "shuffle") { mirror.shuffle = val (0, 0, 127); editShuffle(); return true; }
    if (n == "clearTrack")
    {
        const int t = track (0); if (t < 0) return false;
        auto& tr = mirror.tracks[(size_t) t]; const auto len = tr.length; const bool m = tr.muted;
        tr = UiTrack(); tr.length = len; tr.muted = m;
        for (int i = 0; i < kSteps; ++i) editStep (t, i);
        return true;
    }
    if (n == "copyTrack")
    {
        const int s = track (0), d = track (1); if (s < 0 || d < 0) return false;
        const bool m = mirror.tracks[(size_t) d].muted; const auto len = mirror.tracks[(size_t) s].length;
        mirror.tracks[(size_t) d] = mirror.tracks[(size_t) s]; mirror.tracks[(size_t) d].muted = m; mirror.tracks[(size_t) d].length = len;
        editLength (d); for (int i = 0; i < kSteps; ++i) editStep (d, i);
        return true;
    }
    return false;
}

// ---- state ------------------------------------------------------------------------------------------------------
std::string SeqBridge::serialize() const
{
    std::string s; s.push_back (1); s.push_back ((char) mirror.shuffle);
    for (const auto& t : mirror.tracks)
    {
        s.push_back ((char) t.length); s.push_back (t.muted ? 1 : 0);
        for (int i = 0; i < kSteps; ++i)
        {
            const size_t k = (size_t) i;
            for (std::uint8_t v : { t.on[k], t.vol[k], t.prob[k], t.note[k], t.flam[k], t.shift[k] }) s.push_back ((char) v);
        }
    }
    return s;
}

bool SeqBridge::deserialize (const std::uint8_t* d, size_t n)
{
    if (n != 2 + (size_t) kTracks * (2 + kSteps * 6) || d[0] != 1) return false;
    UiPattern p; p.shuffle = std::min<std::uint8_t> (d[1], 127);
    size_t o = 2;
    for (auto& t : p.tracks)
    {
        t.length = std::clamp<std::uint8_t> (d[o++], 1, 64); t.muted = d[o++] != 0;
        for (int i = 0; i < kSteps; ++i)
        {
            const size_t k = (size_t) i;
            t.on[k] = d[o++] ? 1 : 0; t.vol[k] = std::clamp<std::uint8_t> (d[o++], 1, 127); t.prob[k] = std::clamp<std::uint8_t> (d[o++], 1, 100);
            t.note[k] = std::min<std::uint8_t> (d[o++], 127); t.flam[k] = std::min<std::uint8_t> (d[o++], 5); t.shift[k] = std::min<std::uint8_t> (d[o++], 14);
        }
    }
    mirror = p;
    return true;
}

// ---- audio thread -----------------------------------------------------------------------------------------------
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
                lxrseq_set_main_step (q, 0, c.track, c.idx, c.on);
                lxrseq_set_step (q, 0, c.track, c.idx, c.vol, c.prob, c.note);
                lxrseq_set_step_timing (q, 0, c.track, c.idx, c.flam, c.shift);
                break;
            case SeqCommand::Length:  lxrseq_set_track_length (q, 0, c.track, c.value); break;
            case SeqCommand::Mute:    lxrseq_set_mute (q, c.track, c.value); break;
            case SeqCommand::Shuffle: lxrseq_set_pattern_shuffle (q, 0, c.value); break;
            case SeqCommand::Audition: lxr_trigger (host.raw(), c.track, 60, c.vol); break;
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
    bpmShown.store ((float) bpm, std::memory_order_relaxed);
}

SeqBridge::Level SeqBridge::readLevel() noexcept { return { peakL.exchange (0.f, std::memory_order_relaxed), peakR.exchange (0.f, std::memory_order_relaxed) }; }

SeqBridge::Playhead SeqBridge::readPlayhead() const noexcept
{
    const auto w = playheadWord.load (std::memory_order_relaxed);
    Playhead p { ((w >> 56) & 1) != 0, {}, (double) bpmShown.load (std::memory_order_relaxed) };
    for (int t = 0; t < kTracks; ++t) p.steps[(size_t) t] = (int) ((w >> (8 * t)) & 0xff);
    return p;
}
} // namespace lynn
