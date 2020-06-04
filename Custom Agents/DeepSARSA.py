import numpy as np

from Agents.deepQ import DeepQ
from Agents.episodicExperienceBuffer import EpisodicExperienceBuffer


class CustomAgent(DeepQ):
    displayName = 'Deep SARSA'

    def __init__(self, *args):
        super().__init__(*args)
        self.memory = EpisodicExperienceBuffer(5, 655360, (np.array(self.state_size), 0, 0, None, False))

    def addToMemory(self, state, action, reward, new_state, _, done):
        self.memory.add_transition(state, action, reward, _, done, truncate_episode=done)

    def sample(self):
        return self.memory.sample_randomly_in_episode(self.batch_size, 2)

    def calculateTargetValues(self, mini_batch):
        states, actions, rewards, _, dones = mini_batch

        X_train = np.zeros((self.batch_size,) + self.state_size)
        next_states = np.zeros((self.batch_size,) + self.state_size)

        for sample_index in range(self.batch_size):
            X_train[sample_index] = states[sample_index][0]
            next_states[sample_index] = states[sample_index][1]

        Y_train = self.model.predict(X_train)
        qnext = self.target.predict(next_states)

        for sample_index in range(self.batch_size):
            if dones[sample_index][0]:
                Y_train[sample_index][actions[sample_index][0]] = rewards[sample_index][1]
            else:
                Y_train[sample_index][actions[sample_index][0]] = rewards[sample_index][1] + qnext[sample_index][actions[sample_index][1]] * self.gamma
        return X_train, Y_train
