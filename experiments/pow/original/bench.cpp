#include <cmath>
#include <chrono>
#include <cstdint>
#include <algorithm>
#include <iostream>
#include <vector>

int main() {
    constexpr uint32_t N = 2'000'000;
    constexpr double SCALE = 1.0 / 9007199254740992.0;
    std::vector<double> times;
    double checksum = 0;

    for (int trial = 0; trial < 7; ++trial) {
        uint64_t s = 2026;
        double sum = 0;
        auto t = std::chrono::steady_clock::now();

        for (uint32_t i = 0; i < N; ++i) {
            s = s * 6364136223846793005ULL
                  + 1442695040888963407ULL;
            double u = double(s >> 11) * SCALE;
            uint64_t rot = (s << 29) | (s >> 35);
            double v = double(rot >> 11) * SCALE;
            double x = 0.5 + 1.5 * u;
            double y = -8.0 + 16.0 * v;
            sum += std::pow(x, y);
        }

        auto elapsed = std::chrono::duration<double, std::nano>(
            std::chrono::steady_clock::now() - t).count();
        checksum = sum;
        times.push_back(elapsed / N);
    }

    std::sort(times.begin(), times.end());
    std::cout << "C++      " << times[3]
              << " ns/op  sum=" << checksum << '\n';
}
