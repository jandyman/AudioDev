import("stdfaust.lib");

cutoff = nentry("Lowpass Cutoff Hz", 50, 1, 500, 1);
// threshold = nentry("Threshold", 0.1, 0, 1, 0.001);

// diff = _ <: _, mem : -;

peakDetect(x) = smoothed, diff
with {
    smoothed = x : fi.lowpass(2, cutoff);
    diff = smoothed <: _ , mem : -;
};

process = peakDetect;