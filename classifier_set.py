# Shabnam Nazmi.
# Graduate research assistant at electrical and computer engineering department,
# North Carolina A&T State University, Greensboro, NC.
# snazmi@aggies.ncat.edu.
#
# ------------------------------------------------------------------------------
from math import sqrt
from copy import deepcopy

from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import chebyshev, mahalanobis

from classifier_methods import ClassifierMethods
from classifier import Classifier, build_match
from graph_partitioning import GraphPart
from prediction import aggregate_prediction, one_threshold
from config import *


def match(classifier, state, dtypes):
    for idx, ref in enumerate(classifier.specified_atts):
        x = state[ref]
        if dtypes[ref]:
            if classifier.condition[idx][0] <= x <= classifier.condition[idx][1]:
                pass
            else:
                return False
        else:
            if x == classifier.condition[idx]:
                pass
            else:
                return False
    return True


def similarity(classifier, state):
    center = [(att[1] + att[0]) / 2 for att in classifier.condition]
    x = [state[idx] for idx in classifier.specified_atts]
    try:
        cos = cosine_similarity([center, x])[0][1] / classifier.specified_atts.__len__()
        return cosine_similarity([center, x])[0][1] / classifier.specified_atts.__len__()
    except ValueError:
        return 0.0


def distance(classifier, state, cov_inv=None):
    atts = classifier.specified_atts
    center_sparse = [(att[1] + att[0]) / 2 for att in classifier.condition]
    center = [center_sparse[atts.index(i)] if i in atts else state[i] for i in range(state.__len__())]
    d_mah = mahalanobis(center, state, cov_inv)/atts.__len__()
    # try:
    #     d_cos = 1.0 - cosine_similarity([center_sparse, [state[i] for i in atts]])[0][1]
    # except ValueError:
    #     d_cos = 1.0
    # d_euc = (sqrt(sum([(state[att] - center[idx])**2 for (idx, att)
    #                   in enumerate(atts)]))) / atts.__len__()
    # d_cheby = chebyshev(center_sparse, [state[i] for i in atts])
    return d_mah


def coverage(classifier, data, dtypes):
    covered_samples = []
    for sample in data:
        if match(classifier, sample[0], dtypes):
            covered_samples.append(sample)
    # ds = [distance(classifier, sample[0]) for sample in covered_samples]
    # d_sorted_index = sorted(range(ds.__len__()), key=lambda x: ds[x])
    # knn_samples = [data[idx] for idx in d_sorted_index[:50]]
    return covered_samples


def ga_coverage(classifier, data, dtypes):
    for sample in data:
        if match(classifier, sample[0], dtypes):
            return True
    return False


class ClassifierSets(ClassifierMethods, GraphPart):
    def __init__(self, attribute_info, dtypes, rand_func, sim_delta, sim_mode='global', clustering_method=None,
                 cosine_matrix=None, popset=None, data_cov_inv=None):
        ClassifierMethods.__init__(self, dtypes)
        GraphPart.__init__(self, sim_delta)
        self.popset = []
        self.matchset = []
        self.correctset = []
        self.micro_pop_size = 0
        self.ave_generality = 0.0
        self.ave_fitness = 0.0
        self.classifier = Classifier()
        self.attribute_info = attribute_info
        self.dtypes = dtypes
        self.random = rand_func
        self.cosine_matrix = cosine_matrix
        self.k = MAX_CLASSIFIER

        if popset:
            self.popset = popset

        if sim_mode == 'global' and not cosine_matrix.any():
            raise Exception('similarity matrix required when sim_mode==Global!')
        if sim_mode == 'global':
            self.sim_mode = 1
        else:
            self.sim_mode = 0

        if clustering_method not in [None, 'hfps', 'wsc']:
            raise Exception('undefined clustering method!')
        if clustering_method == 'hfps':
            self.clustering_method = 1
        elif clustering_method == 'wsc':
            self.clustering_method = 2
        else:
            self.clustering_method = 0
        if data_cov_inv.any():
            self.cov_inv = data_cov_inv

    def make_matchset(self, state, target, it):
        covering = True
        self.matchset = [ind for (ind, classifier) in enumerate(self.popset) if
                         match(classifier, state, self.dtypes)]
        if self.matchset.__len__() > self.k:
            d = [distance(self.popset[idx], state, self.cov_inv) for idx in self.matchset]
            sorted_index = sorted(range(d.__len__()), key=lambda x: d[x])
            self.matchset = sorted([self.matchset[idx] for idx in sorted_index[:self.k]])

        if self.matchset.__len__() > 0:
            lbls = set.union(*[self.popset[idx].prediction for idx in self.matchset])
            if target.issubset(lbls):
                covering = False
        # for ind in self.matchset:
        #     if self.popset[ind].prediction == target:
        #         covering = False
        #         return target

        if covering:
            numerosity_sum = sum([self.popset[idx].numerosity for idx in self.matchset])
            new_classifier = Classifier()
            new_classifier.classifier_cover(numerosity_sum + 1, it, state, target,
                                            self.attribute_info, self.dtypes, self.random)
            new_classifiers, pop_reduce = self.apply_partitioning(it, [new_classifier])
            if new_classifiers.__len__() > 0:
                for cl in new_classifiers:
                    new_classifier = Classifier()
                    new_classifier.classifier_cover(numerosity_sum + 1, it, state, cl.prediction,
                                                    self.attribute_info, self.dtypes, self.random)
                    self.insert_classifier_pop(new_classifier, True)
                    self.matchset.append(self.popset.__len__() - 1)
            else:
                self.insert_classifier_pop(new_classifier, True)
                self.matchset.append(self.popset.__len__() - 1)
        else:
            matching_cls = [self.popset[idx] for idx in self.matchset]
            new_classifiers, pop_reduce = self.apply_partitioning(it, matching_cls)
            if new_classifiers.__len__() > 0:
                [self.insert_classifier_pop(classifier, True) for classifier in new_classifiers]
                self.matchset += [self.popset.__len__() - 1 - i for i in range(new_classifiers.__len__())]
                remove_idx = [idx for idx in self.matchset if self.popset[idx].numerosity == 0]
                i = 0
                for idx in remove_idx:
                    self.remove_from_pop(idx - i)
                    self.remove_from_matchset(idx - i)
                    i += 1
                self.micro_pop_size -= pop_reduce

    def make_eval_matchset(self, state):
        self.matchset = [ind for (ind, classifier) in enumerate(self.popset) if
                         match(classifier, state, self.dtypes)]

        if self.matchset.__len__() > self.k:
            d = [distance(self.popset[idx], state, self.cov_inv) for idx in self.matchset]
            sorted_index = sorted(range(d.__len__()), key=lambda x: d[x])
            self.matchset = [self.matchset[idx] for idx in sorted_index[:self.k]]

    def make_correctset(self, target):
        # self.correctset = [ind for ind in self.matchset if self.popset[ind].prediction == target]
        self.correctset = [ind for ind in self.matchset if self.popset[ind].prediction.issubset(target)]

    def apply_partitioning(self, it, matching_cls, vote=None):
        if self.sim_mode == 1:
            graph_valid = self.build_sim_graph(matching_cls, self.cosine_matrix)
        else:
            graph_valid = self.build_sim_graph(matching_cls)

        if graph_valid:
            if self.clustering_method == 2 and not vote:
                raise Exception('vote vector required when clustering_method == wsc!')
            self.cluster_labels(self.clustering_method, vote)
            new_classifiers, pop_reduce = self.refine_prediction(it, matching_cls)
            return new_classifiers, pop_reduce
        else:
            return [], 0

# deletion methods
    def deletion(self):
        while self.micro_pop_size > MAX_CLASSIFIER:
            self.delete_from_sets()

    def delete_from_sets(self):
        ave_fitness = sum([classifier.fitness * classifier.numerosity for classifier in self.popset])\
                       / float(self.micro_pop_size)
        deletion_vote = ClassifierMethods.get_deletion_vote
        vote_list = [deletion_vote(self, cl, ave_fitness) for cl in self.popset]
        vote_sum = sum(vote_list)
        choice_point = vote_sum * self.random.random()

        new_vote_sum = 0.0
        for idx in range(vote_list.__len__()):
            new_vote_sum += vote_list[idx]
            if new_vote_sum > choice_point:
                cl = self.popset[idx]
                cl.update_numerosity(-1)
                self.micro_pop_size -= 1
                if cl.numerosity < 1:
                    self.remove_from_pop(idx)
                    self.remove_from_matchset(idx)
                    self.remove_from_correctset(idx)
                return

    def remove_from_pop(self, ref):
        self.popset.pop(ref)

    def remove_from_matchset(self, ref):
        try:
            self.matchset.remove(ref)
            matchset_copy = [ind-1 if ind > ref else ind for ind in self.matchset]
            self.matchset = matchset_copy
        except ValueError:
            pass

    def remove_from_correctset(self, ref):
        try:
            self.correctset.remove(ref)
        except ValueError:
            pass
        correctset_copy = [ind - 1 if ind > ref else ind for ind in self.correctset]
        self.correctset = correctset_copy

# genetic algorithm methods
    def apply_ga(self, iteration, state, data):
        changed0 = False

        if self.correctset.__len__() > 1:
            parent1, parent2, offspring1, offspring2 = self.selection(iteration)
            if self.random.random() < P_XOVER and not ClassifierMethods.is_equal(self, offspring1, offspring2):
                offspring1, offspring2, changed0 = self.xover(offspring1, offspring2)
            offspring1.condition, offspring1.specified_atts, changed1 = self.mutate(offspring1, state)
            offspring2.condition, offspring2.specified_atts, changed2 = self.mutate(offspring2, state)
        else:
            parent1 = self.popset[self.correctset[0]]
            parent2 = parent1
            offspring1 = Classifier()
            offspring1.classifier_copy(parent1, iteration)
            offspring2 = Classifier()
            offspring2.classifier_copy(parent2, iteration)

            offspring1.condition, offspring1.specified_atts, changed1 = self.mutate(offspring1, state)
            offspring2.condition, offspring2.specified_atts, changed2 = self.mutate(offspring2, state)

        if changed0:
            offspring1.set_fitness(FITNESS_RED * (offspring1.fitness + offspring2.fitness)/2)
            offspring2.set_fitness(offspring1.fitness)
        else:
            offspring1.set_fitness(FITNESS_RED * offspring1.fitness)
            offspring2.set_fitness(FITNESS_RED * offspring2.fitness)

        if ga_coverage(offspring1, data, self.dtypes):
            self.insert_discovered_classifier(offspring1, parent1, parent2)
        if ga_coverage(offspring2, data, self.dtypes):
            self.insert_discovered_classifier(offspring2, parent1, parent2)

    def selection(self, iteration):
        fitness = [self.popset[i].fitness for i in self.correctset]
        if SELECTION == 'r':
            roulette = self.roulette(fitness)
            parent1 = self.popset[next(roulette)]
            parent2 = self.popset[next(roulette)]
        elif SELECTION == 't':
            candidates = [self.popset[idx] for idx in self.correctset]
            parent1 = self.tournament(candidates)
            candidates.remove(parent1)
            parent2 = self.tournament(candidates)
        else:
            print("Error: GA selection method not identified.")
            return

        offspring1 = Classifier()
        offspring1.classifier_copy(parent1, iteration)
        offspring2 = Classifier()
        offspring2.classifier_copy(parent2, iteration)

        return [parent1, parent2, offspring1, offspring2]

    def roulette(self, fitness):
        total = float(sum(fitness))
        n = 2
        i = 0
        w, v = fitness[0], self.correctset[0]
        while n:
            x = total * (1 - self.random.random() ** (1.0 / self.correctset.__len__()))
            total -= x
            while x > w:
                x -= w
                i += 1
                w, v = fitness[i], self.correctset[i]
            w -= x
            yield int(v)
            n -= 1

    def tournament(self, candidates, tsize=5):
        for i in range(candidates.__len__()):
            candidates = self.random.sample(candidates, min(candidates.__len__(), tsize))
            return max(candidates, key=lambda x: x.fitness)

    def xover(self, offspring1, offspring2):
        changed = False
        atts_child1 = offspring1.specified_atts
        atts_child2 = offspring2.specified_atts
        cond_child1 = offspring1.condition
        cond_child2 = offspring2.condition

        def swap1(att0):
            cond_child2.append(cond_child1.pop(atts_child1.index(att0)))
            atts_child2.append(att0)
            atts_child1.remove(att0)
            return True

        def swap2(att0):
            cond_child1.append(cond_child2.pop(atts_child2.index(att0)))
            atts_child1.append(att0)
            atts_child2.remove(att0)
            return True

        def swap3(att0):
            idx1 = atts_child1.index(att0)
            idx2 = atts_child2.index(att0)
            if self.dtypes[att0]:  # Continuous attribute
                choice_key = self.random.randint(0, 3)
                if choice_key == 0:  # swap min of the range
                    cond_child1[idx1][0], cond_child2[idx2][0] = cond_child2[idx2][0], cond_child1[idx1][0]
                elif choice_key == 1:  # swap max of the range
                    cond_child1[idx1][1], cond_child2[idx2][1] = cond_child2[idx2][1], cond_child1[idx1][1]
                elif choice_key == 2:  # absorb ranges into child 1
                    cond_child1[idx1] = [min(cond_child1[idx1][0], cond_child2[idx2][0]),
                                         max(cond_child1[idx1][1], cond_child2[idx2][1])]
                    cond_child2.pop(idx2)
                    atts_child2.remove(att0)
                else:  # absorb ranges into child 2
                    cond_child2[idx2] = [min(cond_child1[idx1][0], cond_child2[idx2][0]),
                                         max(cond_child1[idx1][1], cond_child2[idx2][1])]
                    cond_child1.pop(idx1)
                    atts_child1.remove(att0)
            else:  # Discrete attribute
                cond_child1[idx1], cond_child2[idx2] = cond_child2[idx2], cond_child1[idx1]
            return True

        changed = [swap1(att) for att in set(atts_child1).difference(set(atts_child2)) if self.random.random() < 0.5]
        changed = [swap2(att) for att in set(atts_child2).difference(set(atts_child1)) if self.random.random() < 0.5]
        changed = [swap3(att) for att in set(atts_child1).intersection(set(atts_child2)) if self.random.random() < 0.5]

        offspring1.condition = cond_child1
        offspring1.specified_atts = atts_child1
        offspring2.condition = cond_child2
        offspring2.specified_atts = atts_child2

        return [offspring1, offspring2, changed]

    def mutate(self, child_classifier, state):
        og = True
        changed = False
        atts_child = []
        cond_child = []

        while og:
            atts_child = deepcopy(child_classifier.specified_atts)
            cond_child = deepcopy(child_classifier.condition)

            def mutate_single(idx):
                if idx in atts_child:  # attribute specified in classifier condition
                    if self.random.random() < PROB_HASH:  # remove the specification
                        ref_2_cond = atts_child.index(idx)
                        atts_child.remove(idx)
                        cond_child.pop(ref_2_cond)
                        return True
                    elif self.dtypes[idx]:  # continuous attribute
                        mutate_range = self.random.random() * float(self.attribute_info[idx][1] -
                                                                    self.attribute_info[idx][0]) / 2
                        if self.random.random() < 0.5:  # mutate min of the range
                            if self.random.random() < 0.5:  # add
                                cond_child[atts_child.index(idx)][0] += mutate_range
                            else:  # subtract
                                cond_child[atts_child.index(idx)][0] -= mutate_range
                                cond_child[atts_child.index(idx)][0] = max(cond_child[atts_child.index(idx)][0],
                                                                           self.attribute_info[idx][0])
                        else:  # mutate max of the range
                            if self.random.random() < 0.5:  # add
                                cond_child[atts_child.index(idx)][1] += mutate_range
                                cond_child[atts_child.index(idx)][1] = min(cond_child[atts_child.index(idx)][1],
                                                                           self.attribute_info[idx][1])
                            else:  # subtract
                                cond_child[atts_child.index(idx)][1] -= mutate_range
                        cond_child[atts_child.index(idx)].sort()
                        return True
                    else:
                        pass
                else:  # attribute not specified in classifier condition
                    if self.random.random() < (1 - PROB_HASH):
                        atts_child.append(idx)
                        cond_child.append(build_match(state[idx], self.attribute_info[idx],
                                                                      self.dtypes[idx], self.random))
                        return True
                    return False

            changed = [mutate_single(att_idx) for att_idx in range(self.attribute_info.__len__())
                       if self.random.random() < P_MUT]
            if atts_child.__len__() > 0:
                og = False
        return [cond_child, atts_child, changed]

    def insert_classifier_pop(self, classifier, search_matchset=False):
        existing_classifier = self.get_identical(classifier, search_matchset)
        if isinstance(existing_classifier, Classifier):
            existing_classifier.update_numerosity(1)
        else:
            self.popset.append(classifier)
        self.micro_pop_size += 1

    def insert_discovered_classifier(self, offspring, parent1, parent2):
        if DO_SUBSUMPTION:
            if offspring.specified_atts.__len__() > 0:
                self.subsume_into_parents(offspring, parent1, parent2)
        else:
            self.insert_classifier_pop(offspring)

    def get_identical(self, classifier, search_matchset=False):
        if search_matchset:
            identical = [self.popset[ref] for ref in self.matchset if
                         ClassifierMethods.is_equal(self, classifier, self.popset[ref])]
            if identical:
                return identical[0]
        else:
            identical = [cl for cl in self.popset if
                         ClassifierMethods.is_equal(self, classifier, cl)]
            if identical:
                return identical[0]
        return None

    def get_time_average(self):
        numerosity_sum = sum([self.popset[idx].numerosity for idx in self.correctset])
        time_sum = sum([(self.popset[idx].ga_time * self.popset[idx].numerosity) for idx in self.correctset])
        return time_sum / float(numerosity_sum)

# subsumption methods
    def subsume_into_parents(self, offspring, parent1, parent2):
        if ClassifierMethods.subsumption(self, parent1, offspring):
            self.micro_pop_size += 1
            parent1.update_numerosity(1)
        elif ClassifierMethods.subsumption(self, parent2, offspring):
            self.micro_pop_size += 1
            parent2.update_numerosity(1)
        else:
            self.subsume_into_correctset(offspring)

    def subsume_into_correctset(self, classifier):
        choices = [ref for ref in self.correctset if
                   ClassifierMethods.subsumption(self, self.popset[ref], classifier)]
        if choices:
            idx = self.random.randint(0, choices.__len__()-1)
            self.popset[choices[idx]].update_numerosity(1)
            self.micro_pop_size += 1
            return
        self.insert_classifier_pop(classifier)

    def subsume_correctset(self):
        if self.correctset.__len__() > 1:
            subsumer = None
            compare_list = self.correctset.copy()
            for ref in self.correctset:
                if ClassifierMethods.is_subsumer(self, self.popset[ref]):
                    subsumer = self.popset[ref]
                    compare_list = compare_list.remove(ref)
                    break

            if subsumer and compare_list:
                delete_list = [ref for ref in compare_list if
                               ClassifierMethods.is_more_general(self, subsumer, self.popset[ref])]
                sub = 0
                for ref in delete_list:
                    ref -= sub
                    subsumer.update_numerosity(self.popset[ref].numerosity)
                    self.remove_from_pop(ref)
                    self.remove_from_matchset(ref)
                    self.remove_from_correctset(ref)
                    sub += 1
            else:
                return

# update sets
    def update_sets(self, target):
        m_size = sum([self.popset[ref].numerosity for ref in self.matchset])
        [self.popset[ref].update_params(m_size, target) for ref in self.matchset]

    def estimate_label_pr(self, data):
        for cl in self.popset:
            cl.estimate_label_based([sample[1] for sample in coverage(cl, data, self.dtypes)])

    def clear_sets(self):
        self.matchset = []
        self.correctset = []

# evaluation methods
    def pop_average_eval(self, no_features):
        generality_sum = sum([(no_features - classifier.specified_atts.__len__())/float(no_features)
                              for classifier in self.popset])
        fitness_sum = sum([classifier.fitness for classifier in self.popset])
        try:
            self.ave_generality = generality_sum / float(self.popset.__len__())
            self.ave_fitness = fitness_sum / float(self.popset.__len__())
        except ZeroDivisionError:
            self.ave_generality = None
            self.ave_fitness = None

    def pop_compaction(self):
        self.popset = [classifier for classifier in self.popset if classifier.match_count > 0]

# other methods
    def get_pop_tracking(self):
        tracking = str(self.popset.__len__()) + ", " + str(self.micro_pop_size) \
                   + ", " + str("%.4f" % self.ave_fitness) + ", " + str("%.4f" % self.ave_generality)
        return tracking
