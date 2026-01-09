# Project Concept

The project is an algorithm for shifting the pitch of bass guitar signals down in pitch. A typical application is an octave dropper, but the only real limitation in terms of pitch interval is that the pitch can only be shifted down.

The core idea behind the algorithm is to store the incoming signal in delay line, and to play back a signal out of the delay line at a reduced sampling rate, which implies fractional delays for anything besides and octave drop. The delay time increases by a constant for each output sample, effectively lowering the pitch of the output signal. But the delay time needs to be set/reset at certain times, both to preserve attack transients and to limit output latency.

The delay time is reset in a disontiguous fashion based on two different triggers, described below. In order to prevent clicks, two delay lines sharing the same delay buffer operate in ping pong fashion so that a quick cross fade can be implemented at set/reset points.

The first trigger, which has the higher precedence, is an input from an attack detector. It causes a delay time transition to a delay of zero, using the cross fade technique described above. This reset to a virtually zero delay allows the early attack portion of a new note to be represented properly. A latency counter is set to zero, which is used for the second trigger.

The second lower priority trigger is used during the sustain portion of a note. During the sustain portion of the note, the latency will gradually increase. At a certain point, it will become desirable to reset the delay time to reduce the latency. In order to reduce or eliminate any artifacts, we try to reset the delay times such that the outputs jumps from one zero crossing to another at multiples of the period of the waveform. We will describe the "looping" strategy in more detail in later sections. There is a trade off concerning when you want to try to reset the delay time. If you wait longer, more latency will accumulate, but you will retain more of the character of the attack.

# Functional block breakdown and high level design

## Attack Detector

This block detects attack transients. The output is zero for any sample which does not represent an attack, and one for a sample which represents an attack detection. So it is a series of isolated impulse spikes. The output is sent to the control logic

## Zero Crossing Detector

This block looks for zero crossings as they arrive. In a manner similar to the Attack Detector, it outputs a stream which contains a series of of isolated impulses representing zero crossings. 


## Dual Fractional Delay Line

This block contains a delay buffer of a fixed size. It has three inputs, the input signal and two delay time inputs. It has two outputs, corresponding to the delayed input signal and the two delay time signals.

## Control Logic

Takes the inputs from the attack detector and the zero crossing detector, and determines when to reset the delay lines. It manages the cross fades and overall state. It has two outputs, which are the two delay time for the dual delay line. 

There are two triggers for resetting the delay times and initiating a cross fade. One is when an impulse is received from the attack detector. The other is when the looping logic determines that it is time to reset the delay time to an less value, matching up two zero crossings an integer number of pitch periods apart. The attack detector input is a higher priority. No matter what the looping logic is doing, if an attack is detected, a cross fade takes place. The looping logic is more complex than the attack detector, and requires a separate explanation.

### Sustain Portion Looping logic

In order to find loop points where the delay times are reset, we need to keep a record of the zero crossing points based on input from the zero crossing detector. We record the playback time for each zero crossing along with the arrival time. This can be calculated based on the (instantaneous) delay time and the arrival time (PT = AT + DT). This data is used in the following procedure where we look for candidate looping opportunities

As each zero crossing arrives, the first check is the current latency. If the latency is below a certain threshold, no action is taken other than storing the record as described above. If the latency is above threshold, the looping logic examines the previous zero crossing records.

For each record in the zero crossing list, if the current time is greater than the playback time, then that zero crossing has already been played, and as such is not a candidate, so that record is removed from the list.

The next test is to compare the playback time of zero crossings in the list to the latest zero crossing. The idea is to only choose difference in playback times consistent with the plausible period of the input waveform. If we find a candidate, we schedule a zero crossing transition. This zero crossing transition will occur at the playback time of the earlier zero crossing. At that time, the delay time will transition to the delay time equivalent to the playback time of the current zero crossing. So at that transition time, the delay time will be set to playback time of current zero crossing minus the transition time.

If no transition candidate is found, the current zero crossing is stored and no action is taken. There will need to be an upper limit latency threshold where a reset of the delay time is scheduled, but with longer crossfade time. This is our "bailout strategy" for looping, and will likely occur in noise tails or other unresolvable situations