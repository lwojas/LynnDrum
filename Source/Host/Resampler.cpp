// SPDX-License-Identifier: GPL-3.0-only
#include "Resampler.h"
#include <cmath>
#include <algorithm>

namespace lynn
{
namespace
{
double besselI0 (double x)
{
    double sum = 1.0, term = 1.0;
    for (int k = 1; k < 60; ++k) { term *= (x / (2.0 * k)) * (x / (2.0 * k)); sum += term; if (term < 1e-18 * sum) break; }
    return sum;
}
}

void Resampler::prepare (double srcRate, double dstRate)
{
    step = srcRate / dstRate;
    // anti-aliasing / anti-imaging cutoff relative to the source Nyquist: below 1 when down-sampling
    const double fc = std::min (1.0, dstRate / srcRate) * 0.94;
    const double beta = 9.0;                                  // ~ 100 dB stop band
    const double invI0 = 1.0 / besselI0 (beta);
    table.assign (static_cast<size_t> (kPhases + 1) * kTaps, 0.f);
    const double halfLen = kTaps / 2.0;
    for (int p = 0; p <= kPhases; ++p)
    {
        const double frac = static_cast<double> (p) / kPhases;       // fractional position of the output sample
        double sum = 0.0;
        for (int t = 0; t < kTaps; ++t)
        {
            // tap t sits at source index (base - T/2 + 1 + t); distance from output position:
            const double x = (t - kTaps / 2 + 1) - frac;
            const double sinc = std::fabs (x) < 1e-12 ? fc : std::sin (M_PI * fc * x) / (M_PI * x);
            const double r = x / halfLen;
            const double win = std::fabs (r) >= 1.0 ? 0.0 : besselI0 (beta * std::sqrt (1.0 - r * r)) * invI0;
            const double h = sinc * win;
            table[static_cast<size_t> (p) * kTaps + t] = static_cast<float> (h);
            sum += h;
        }
        if (sum != 0.0)                                       // unity DC gain for every phase
            for (int t = 0; t < kTaps; ++t) table[static_cast<size_t> (p) * kTaps + t] = static_cast<float> (table[static_cast<size_t> (p) * kTaps + t] / sum);
    }
    ringL.assign (kRing, 0.f); ringR.assign (kRing, 0.f);
    reset();
}

void Resampler::reset()
{
    std::fill (ringL.begin(), ringL.end(), 0.f);
    std::fill (ringR.begin(), ringR.end(), 0.f);
    written = 0;
    pos = kTaps / 2 + 1;               // the first output sample sits after the (silent) history
    written = static_cast<std::int64_t> (pos);   // pretend the history was produced (zeros)
}
} // namespace lynn
