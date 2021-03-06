import numpy as np
from collections import deque

def ddpg(env, agent, n_episodes, eps_start=0., eps_min=0., eps_decay=0., beta_start=1., beta_end=1., continue_after_solved=True):
    """highly modified Deep Deterministic Policy Gradient
    (DDPG + Prioritized Experience Replay + Dueling Architecture + Distribution + Noisy Layers)
    (I'm not sure if there's any official name or similar methods)

    Params
    ======
        env (UnityEnvironment): Unity environment instance
        agent (Agent): the agent to be trained
        n_episodes (int): maximum number of training episodes
        eps_start (float): initial epsilon value for gaussian noise
        eps_min (float): minimum value for epsilon
        eps_decay (float): epsilon decay factor
        beta_start (float): initial importance-sampling weight for prioritized experience replay
        beta_end (float): final importance-sampling weight for prioritized experience replay
        continue_after_solved (bool): whether to continue training after reaching the average score 30
    """
    brain_name = env.brain_names[0]
    num_agents = agent.n_agents

    solved = False
    mean_scores = []
    mean_scores_window = deque(maxlen=100)

    eps = eps_start

    agent.beta = beta_start

    actor_noisy_params  = [param for name, param in agent.actor_local.named_parameters()
                           if name.endswith('noisy_weight') or name.endswith('noisy_bias')]
    critic_noisy_params = [param for name, param in agent.critic_local.named_parameters()
                           if name.endswith('noisy_weight') or name.endswith('noisy_bias')]

    report_str_basic_format = "\rEpisode {:d} | Total Steps (all agents): {:d}"\
        " | Current Average Score: {:>6.3f} | Last 100 Average Score: {:>6.3f}"\
        " | Epsilon: {:>6.4f} | A: {:>6.4f} | Beta: {:>6.4f}"
    report_str = report_str_basic_format.format(0, 0, 0, 0, eps, agent.a, agent.beta)

    n_steps_taken = 0
    try:
        for i_episode in range(1, n_episodes+1):
            env_info = env.reset(train_mode=True)[brain_name]            # reset the environment
            states = env_info.vector_observations                        # get the current state (for each agent)
            scores = np.zeros(num_agents)                                # initialize the score (for each agent)
            t = 0
            while True:
                actions = agent.act(states)                              # choose actions
                if eps:
                    actions = np.clip(actions + eps * np.random.randn(*actions.shape), -1, 1) # add noise
                env_info = env.step(actions)[brain_name]                 # send all actions to the environment
                next_states = env_info.vector_observations               # get next state (for each agent)
                rewards = env_info.rewards                               # get reward (for each agent)
                dones = env_info.local_done                              # see if episode finished
                agent.step(states, actions, rewards, next_states, dones) # take a step
                t += 1
                n_steps_taken += num_agents
                scores += env_info.rewards                               # update the score (for each agent)
                states = next_states                                     # roll over states to next time step
                print(report_str + " *** timestep {:d} ***".format(t), end='')
                if np.any(dones):                                        # exit loop if episode finished
                    break

            agent.reset()                                                # reset the secondary buffer for multisteps

            mean_score = np.mean(scores)                                 # get the average score across all agents
            mean_scores.append(mean_score)                               # append the average score to scores log
            mean_scores_window.append(mean_score)                        # append the average score to scores window

            mean_scores_window_average = np.mean(mean_scores_window)

            report_str = report_str_basic_format.format(i_episode, n_steps_taken,
                                                        mean_score, mean_scores_window_average,
                                                        eps, agent.a, agent.beta)
            if actor_noisy_params:
                flattened_abs_noise = np.concatenate([param.data.abs().cpu().numpy().reshape((-1,))
                                                      for param in actor_noisy_params])
                report_str += " | Avg Actor Noise Magnitude: {:>6.4f} +- {:<6.4f}"\
                              .format(np.mean(flattened_abs_noise), np.std(flattened_abs_noise))
            if critic_noisy_params:
                flattened_abs_noise = np.concatenate([param.data.abs().cpu().numpy().reshape((-1,))
                                                      for param in critic_noisy_params])
                report_str += " | Avg Critic Noise Magnitude: {:>6.4f} +- {:<6.4f}"\
                              .format(np.mean(flattened_abs_noise), np.std(flattened_abs_noise))

            if i_episode % 10 == 0:
                print(report_str, end='\n')
            else:
                print(report_str + "                                     ", end='')

            if not solved and len(mean_scores_window) >= 100 and mean_scores_window_average >= 30:
                print('\nEnvironment solved in {:d} episodes!\tAverage Score: {:.3f}'\
                      .format(i_episode-100, mean_scores_window_average))
                solved = True
                if not continue_after_solved:
                    break

            eps = max(eps_min, eps * eps_decay)
            agent.beta = beta_start + (beta_end - beta_start) * (i_episode / n_episodes)

    except KeyboardInterrupt:
        return mean_scores

    return mean_scores
