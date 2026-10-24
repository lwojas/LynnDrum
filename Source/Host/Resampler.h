// SPDX-License-Identifier: GPL-3.0-only
// LynnDrum - polyphase windowed-sinc resampler, pull based (engine rate -> host rate).
#pragma once
#include <cstdint>
#include <vector>

namespace lynn
{
// Converts a stereo stream produced in fixed chunks at srcRate to dstRate. The source is requested on demand
// through a fill callback, so there is no queue to drain: the only latency is the filter's half length.
class Resampler
{
public:
    static constexpr int kTaps = 64;        // kernel length in source samples (half = look-ahead)
    static constexpr int kPhases = 1024;    // table resolution, linear interpolation between phases
    static constexpr int kRing = 4096;      // power of two

    void prepare (double srcRate, double dstRate);
    void reset();

    // Latency in *source* samples between a sample entering the ring and it reaching its output position.
    double latencySourceSamples() const noexcept { return kTaps / 2; }
    double ratio() const noexcept { return step; }

    // fill (float* l, float* r, int frames): append `frames` new source frames
    template <class Fill>
    void process (float* outL, float* outR, int n, Fill&& fill)
    {
        for (int i = 0; i < n; ++i)
        {
            const std::int64_t base = static_cast<std::int64_t> (pos);          // pos >= 0 always
            while (written <= base + kTaps / 2)                                // need samples up to base + T/2
                refill (fill);
            const double frac = pos - static_cast<double> (base);
            const double fph = frac * kPhases;
            const int p0 = static_cast<int> (fph);
            const float w = static_cast<float> (fph - p0);
            const float* k0 = &table[static_cast<size_t> (p0) * kTaps];
            const float* k1 = k0 + kTaps;                                      // table has kPhases + 1 rows
            float accL = 0.f, accR = 0.f;
            std::int64_t n0 = base - kTaps / 2 + 1;
            for (int t = 0; t < kTaps; ++t)
            {
                const float h = k0[t] + (k1[t] - k0[t]) * w;
                const int idx = static_cast<int> ((n0 + t) & (kRing - 1));
                accL += h * ringL[static_cast<size_t> (idx)];
                accR += h * ringR[static_cast<size_t> (idx)];
            }
            outL[i] = accL; outR[i] = accR;
            pos += step;
        }
    }

private:
    template <class Fill> void refill (Fill& fill)
    {
        constexpr int chunk = 64;
        float l[chunk], r[chunk];
        fill (l, r, chunk);
        for (int i = 0; i < chunk; ++i)
        {
            const size_t idx = static_cast<size_t> ((written + i) & (kRing - 1));
            ringL[idx] = l[i]; ringR[idx] = r[i];
        }
        written += chunk;
    }

    double step = 1.0;                      // source samples per destination sample
    double pos = 0.0;                       // absolute source position of the next output sample
    std::int64_t written = 0;               // source samples produced so far
    std::vector<float> table;               // (kPhases + 1) x kTaps
    std::vector<float> ringL, ringR;
};
} // namespace lynn
