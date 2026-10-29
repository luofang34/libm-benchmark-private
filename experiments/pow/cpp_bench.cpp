#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <vector>
__attribute__((noinline)) double measured_pow(double x,double y) { return std::pow(x,y); }
int main() {
    std::vector<std::array<double,2>> input;
    uint64_t s=2026;
    for (size_t i=0;i<16384;i++) {
        s=s*6364136223846793005ULL+1442695040888963407ULL;
        auto r=(s<<29)|(s>>35);
        input.push_back({0.5+1.5*double(s>>11)/9007199254740992.0,-8+16*double(r>>11)/9007199254740992.0});
    }
    std::cout << "round,ns_per_op,checksum\n";
    for (int round=0;round<20;round++) {
        uint64_t sums[4]={};
        auto start=std::chrono::steady_clock::now();
        for (int repeat=0;repeat<32;repeat++) for (size_t i=0;i<input.size();i++) {
            double x=input[i][0],y=input[i][1];
            asm volatile("" : "+w"(x), "+w"(y));
            double value=measured_pow(x,y);
            uint64_t bits; std::memcpy(&bits,&value,8); sums[i%4]+=bits;
        }
        auto ns=std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-start).count();
        uint64_t sum=sums[0]+sums[1]+sums[2]+sums[3];
        if(round>=5) std::cout << round-5 << ',' << ns/(input.size()*32) << ',' << std::hex << sum << std::dec << '\n';
    }
}
