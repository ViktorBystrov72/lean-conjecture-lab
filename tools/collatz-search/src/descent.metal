#include <metal_stdlib>
using namespace metal;

struct Wide {
    ulong low;
    ulong high;
};

struct Params {
    ulong base_low;
    ulong base_high;
    ulong first_period;
    ulong first_residue;
    ulong bits;
    ulong residue_count;
    ulong max_steps;
};

static bool less_than(Wide a, Wide b) {
    return a.high < b.high || (a.high == b.high && a.low < b.low);
}

static Wide shift_right(Wide x, uint shift) {
    if (shift >= 64) {
        return Wide{x.high >> (shift - 64), 0};
    }
    return Wide{(x.low >> shift) | (x.high << (64 - shift)), x.high >> shift};
}

static uint trailing_zeros(ulong x) {
    uint low = uint(x);
    return low != 0 ? ctz(low) : 32 + ctz(uint(x >> 32));
}

kernel void descent(
    const device uint *residues [[buffer(0)]],
    device uchar *results [[buffer(1)]],
    constant Params &params [[buffer(2)]],
    uint tid [[thread_position_in_grid]]
) {
    // A dispatch spans at most 2^20 slots, so only its global period needs 64 bits.
    uint slot = uint(params.first_residue) + tid;
    uint residue_count = uint(params.residue_count);
    ulong period = params.first_period + slot / residue_count;
    ulong offset = (period << params.bits) + residues[slot % residue_count];
    ulong low = params.base_low + offset;
    Wide start{low, params.base_high + ulong(low < params.base_low)};
    Wide value = start;
    uint left = uint(params.max_steps);
    while (left != 0) {
        if ((value.low & 1) == 0) {
            uint zeros = value.low != 0 ? trailing_zeros(value.low) : 64 + trailing_zeros(value.high);
            uint shift = min(zeros, left);
            value = shift_right(value, shift);
            left -= shift;
        } else {
            // For odd x, (3x + 1)/2 = x + (x >> 1) + 1.
            Wide divided = shift_right(value, 1);
            ulong next_low = value.low + divided.low + 1;
            ulong carry = ulong(next_low <= value.low);
            ulong next_high = value.high + divided.high + carry;
            if (next_high < value.high) {
                results[tid] = 2;
                return;
            }
            value = Wide{next_low, next_high};
            --left;
        }
        if (less_than(value, start)) {
            results[tid] = 1;
            return;
        }
    }
    results[tid] = 2;
}
