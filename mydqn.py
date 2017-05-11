from __future__ import division
import warnings
import numpy as np
from copy import deepcopy
from keras.callbacks import History
from rl.callbacks import TestLogger, TrainEpisodeLogger, TrainIntervalLogger, Visualizer, CallbackList
from rl.agents.dqn import DQNAgent
from myCallback import myTrainEpisodeLogger

class myDQNAgent(DQNAgent):

    def fit(self, env, nb_episodes, action_repetition=1, callbacks=None, verbose=1,
            visualize=False, nb_max_start_steps=0, start_step_policy=None, log_interval=10000,
            nb_max_episode_steps=None):
        if not self.compiled:
            raise RuntimeError('Your tried to fit your agent but it hasn\'t been compiled yet. Please call `compile()` before `fit()`.')
        if action_repetition < 1:
            raise ValueError('action_repetition must be >= 1, is {}'.format(action_repetition))

        self.training = True

        callbacks = [] if not callbacks else callbacks[:]

        if verbose == 1:
            callbacks += [TrainIntervalLogger(interval=log_interval)]
        elif verbose > 1:
            callbacks += [myTrainEpisodeLogger()]
        if visualize:
            callbacks += [Visualizer()]
        history = History()
        #callbacks += [history]
        callbacks = CallbackList(callbacks)
        if hasattr(callbacks, 'set_model'):
            callbacks.set_model(self)
        else:
            callbacks._set_model(self)
        callbacks._set_env(env)
        params = {
            'nb_episodes': nb_episodes,
        }
        if hasattr(callbacks, 'set_params'):
            callbacks.set_params(params)
        else:
            callbacks._set_params(params)
        self._on_train_begin()
        callbacks.on_train_begin()

        self.step = 0
        observation = None
        episode_reward = None
        episode_step = None

        for episode in range(nb_episodes):

            if observation is None:  # start of a new episode
                callbacks.on_episode_begin(episode)
                episode_step = 0
                episode_reward = 0.

                # Obtain the initial observation by resetting the environment.
                self.reset_states()
                observation = deepcopy(env.reset())
                if self.processor is not None:
                    observation = self.processor.process_observation(observation)
                assert observation is not None

                # Perform random starts at beginning of episode and do not record them into the experience.
                # This slightly changes the start position between games.
                nb_random_start_steps = 0 if nb_max_start_steps == 0 else np.random.randint(nb_max_start_steps)
                for _ in range(nb_random_start_steps):
                    if start_step_policy is None:
                        action = env.action_space.sample()
                    else:
                        action = start_step_policy(observation)
                    if self.processor is not None:
                        action = self.processor.process_action(action)
                    callbacks.on_action_begin(action)
                    observation, reward, done, info = env.step(action)
                    observation = deepcopy(observation)
                    if self.processor is not None:
                        observation, reward, done, info = self.processor.process_step(observation, reward, done, info)
                    callbacks.on_action_end(action)
                    if done:
                        warnings.warn('Env ended before {} random steps could be performed at the start. You should probably lower the `nb_max_start_steps` parameter.'.format(nb_random_start_steps))
                        observation = deepcopy(env.reset())
                        if self.processor is not None:
                            observation = self.processor.process_observation(observation)
                        break

            # At this point, we expect to be fully initialized.
            assert episode_reward is not None
            assert episode_step is not None
            assert observation is not None

            done = False
            while not done:

                # Run a single step.
                callbacks.on_step_begin(episode_step)
                # This is were all of the work happens. We first perceive and compute the action
                # (forward step) and then use the reward to improve (backward step).
                action = self.forward(observation)
                if self.processor is not None:
                    action = self.processor.process_action(action)
                reward = 0.
                accumulated_info = {}

                for _ in range(action_repetition):
                    callbacks.on_action_begin(action)
                    observation, r, done, info = env.step(action)
                    observation = deepcopy(observation)
                    if self.processor is not None:
                        observation, r, done, info = self.processor.process_step(observation, r, done, info)
                    for key, value in info.items():
                        if not np.isreal(value):
                            continue
                        if key not in accumulated_info:
                            accumulated_info[key] = np.zeros_like(value)
                        accumulated_info[key] += value
                    callbacks.on_action_end(action)
                    reward += r
                    if done:
                        break
                if nb_max_episode_steps and episode_step >= nb_max_episode_steps - 1:
                    # Force a terminal state.
                    done = True
                metrics = self.backward(reward, terminal=done)
                episode_reward += reward

                step_logs = {
                    'action': action,
                    'observation': observation,
                    'reward': reward,
                    'metrics': metrics,
                    'episode': episode,
                    'info': accumulated_info,
                }
                callbacks.on_step_end(episode_step, step_logs)
                episode_step += 1
                self.step += 1

                if done:
                    # We are in a terminal state but the agent hasn't yet seen it. We therefore
                    # perform one more forward-backward call and simply ignore the action before
                    # resetting the environment. We need to pass in `terminal=False` here since
                    # the *next* state, that is the state of the newly reset environment, is
                    # always non-terminal by convention.
                    self.forward(observation)
                    self.backward(0., terminal=False)

                    # This episode is finished, report and reset.
                    episode_logs = {
                        'episode_reward': episode_reward,
                        'nb_episode_steps': episode_step,
                        'nb_steps': self.step,
                    }
                    callbacks.on_episode_end(episode, episode_logs)

                    episode += 1
                    observation = None
                    episode_step = None
                    episode_reward = None

        callbacks.on_train_end(logs={'did_abort': False})
        self._on_train_end()

        return history