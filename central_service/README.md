### Captain's Log (Training)

### 23/5/2020 - Current
---

Training with:
```
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

```
state[0, -1] = bdw_paths[0] # bandwidth path1
state[1, -1] = bdw_paths[1] # bandwidth path2
state[2, -1] = path1_smoothed_RTT * 100
state[3, -1] = path2_smoothed_RTT * 100
state[4, -1] = path1_retransmissions + path1_losses
state[5, -1] = path2_retransmissions + path2_losses
```

Notes: 
1. Most of the training values are default for Pensieve except:
    1. BATCH_TRAINING_SIZE down to 32 from 100 
2. Only _52_ steps out of _222_ iterations were valid for training.
3. Results of Tensorboard in => figures/23_05_2020
4. **After few iterations, agent selects only Path 0** 
---