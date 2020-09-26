### Captain's Log (Training)


### 9/6/2020 - Current
Training with:
``` json

```

States:
* Same as previous run

Protocol/Training Issues: 
* Same as 23/

Notes:
1. a3c => Modified NN inputs in both Actor and Critic networks
    1. There was a [bug](https://github.com/hongzimao/pensieve/issues/20), which used twice the input state 4
   which in our case represents path1_packet_retransmissions + losses instead of utilizing path2_retr + losses
    2.  In addition, this particular state (`split_4`) was a `conv_1d` layer which did not make sense in our use case, so turned it into `fully_connected layer`
2. a3c => Updated `entropy_weight` to `1.0` for this run, in subsequent runs will reduce it towards 0.1
    1. As stated in the paper the `entropy_weight` begins at `1.0` and decreases till `0.1` (decaying), however this was not
    illustrated in code, where the weight was initialized as `0.5`!
3. agent => Increased batch training size to 100 as original implementation.

Runs:
1. Entropy converged to zero after ~350 epochs. Stopped it.
2. Continuing from 256 of previous run. Restarted whenever entropy covnerged to zero, more than ~1024 epochs
3. 
---

### 26/5/2020 - 9/6/2020
Training with:
``` json
Same as 23/5
```
States:

Normalized State input.
Values used are observations from previous runs.
Bandwidth we already know beforehand it ranges [1, 100].

Formula: (x - min) / (max - mix)
``` python
state[0, -1] = (bdw_paths[0] - 1.0) / (100.0 - 1.0) # bandwidth path1
state[1, -1] = (bdw_paths[1] - 1.0) / (100.0 - 1.0) # bandwidth path2
state[2, -1] = ((path1_smoothed_RTT * 1000.0) - 1.0) / (120.0) # max RTT so far 120ms 
state[3, -1] = ((path2_smoothed_RTT * 1000.0) - 1.0) / (120.0)
state[4, -1] = ((path1_retransmissions + path1_losses) - 0.0) / 20.0
state[5, -1] = ((path2_retransmissions + path2_losses) - 0.0) / 20.0
```

Protocol/Training Issues:
* Same as 23/5

Notes: 
1. Feature normalization
2. **1st Run:** Much better results than previous run (might be random need to run more cases). Overall, training seems to be more stable than in previous training sessions, and the graphs validate that. It seems like the run is converging gradually.
    1. ***Logging happens once per request, it doesn't happen once per training step*** 
    2. Iterations: ~350
    3. Execution time: Similar to 23/5
---


### 23/5/2020 - 26/5/2020

Training with:
``` json
BATCH_TRAINING_SIZE: 32,
GRAPHS_SIZE : 57,
TOPOLOGIES_SIZE: 100,
GRADIENT_BATCH_sIZE: 8,
BROWSER: "Firefox",
GAMMA: 0.99,
ENTROPY_WEIGHT = 0.5,
ENTROPY_EPS = 1e-6,
ACTOR_LR_RATE: 0.0001,
CRITIC_LR_RATE: 0.001,
S_LEN: 8  # take how many frames in the past
```
States: 
``` python
state[0, -1] = bdw_paths[0] # bandwidth path1
state[1, -1] = bdw_paths[1] # bandwidth path2
state[2, -1] = path1_smoothed_RTT * 100
state[3, -1] = path2_smoothed_RTT * 100
state[4, -1] = path1_retransmissions + path1_losses
state[5, -1] = path2_retransmissions + path2_losses
```

Protocol Issues:
1. File size not found (random appearance) leads to:
    1. OBIT Not matching (cryptographic)
2. Packet too large (random appearance)

- When 1. occurs, 1.1. follows immediately after (so two episodes are lost)
- When 2. occurs, next episode is typically _fine_


Training Issues: 
1. Only _52_ steps out of _222_ iterations were valid for training. (rest discarded due to _Active Issues_ above)
2. Results of Tensorboard in => figures/23_05_2020
3. With Firefox, and because of concurrency, network statistics are not updated frequently!!! 

Notes: 
1. Most of the training values are default from Pensieve except:
    1. BATCH_TRAINING_SIZE down to 32 from 100 
2. **First Run:** After few iterations, agent selects only first Path (_5362_ to _486_) (probably local optima) -- **~50 iterations**
3. **Second Run:** More balanced, _~2147_ selections of 1st path and _~3564_ of second path -- **~70 iterations**
4. **Third Run:** More samples than before, again more balance in path selection (does not seem to converge) -- **~100 iterations**
5. **Fourth Run:** Entropy converges to zero again after ~90-100 steps, selects only Path 0 (local optima). -- **~150 iterations** -- **total execution time: ***~3hours20minutes***
6. **Fifth Run:** Entropy gets _very close_ to zero but still not zero, after ~200 steps (best run so far), temporal difference (also converges around 0, maybe a good indication of good results?). -- **~220** execution time: ***~3hours40minutes***

**Fifth Run. fixed logging, now logs per whole episode, instead of logging per training batch (<32) !!!, more accurate than previous graphs**
---
