import signal
from multiprocessing import Pool
import multiprocessing as mp
import sys
import math
import copy
import random
from collections import Counter

from modules.functions import create_position_probability_matrix

def correct_strings(partition_alignments, unique_seq_to_acc, single_core = False):
    S_prime = {}

    partition_unique_seq_to_acc = {}
    for m, partition in partition_alignments.items():
        partition_unique_seq_to_acc[m] = {}
        for s in partition:
            if s in unique_seq_to_acc:
                partition_unique_seq_to_acc[m][s] = unique_seq_to_acc[s]


    if single_core:
        for m, partition in partition_alignments.items():
            S_prime_partition = correct_to_minimizer(m, partition, partition_unique_seq_to_acc[m])
        for acc, s in S_prime_partition.items():
            S_prime[acc] = s

    else:
        ####### parallelize statistical tests #########
        # pool = Pool(processes=mp.cpu_count())
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)
        pool = Pool(processes=mp.cpu_count())
        try:
            res = pool.map_async(correct_to_minimzer_helper, [ ( (m, partition, partition_unique_seq_to_acc[m]), {}) for m, partition in partition_alignments.items() if len(partition) > 1 ] )
            S_prime_partition_dicts =res.get(999999999) # Without the timeout this blocking call ignores all signals.
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, terminating workers")
            pool.terminate()
            sys.exit()
        else:
            print("Normal termination")
            pool.close()
        pool.join()
        for S_prime_partition in S_prime_partition_dicts:
            for acc, s in S_prime_partition.items():
                assert acc not in S_prime
                S_prime[acc] = s


    return S_prime

def correct_to_minimzer_helper(arguments):
    args, kwargs = arguments
    return correct_to_minimizer(*args, **kwargs)

def correct_to_minimizer(m, partition, unique_seq_to_acc):
    S_prime_partition = {}

    N_t = sum([container_tuple[3] for s, container_tuple in partition.items()]) # total number of sequences in partition
    
    if N_t == 2:
        print("Partition has size", N_t, "no meaningful correction can be done")

    if len(partition) > 1 and N_t > 2:
        # all strings has not converged
        alignment_matrix, PFM = create_position_probability_matrix(m, partition) 
        
        # print("minimizer errors:",  math.ceil(min([ partition[s][0] for s in partition if partition[s][3] > 1 or s !=m ]) / 2.0)  )
        # minimizer_errors = min([ partition[s][0] for s in partition if partition[s][3] > 1 or s !=m ])
        # minimizer_errors = math.ceil(min([ partition[s][0] for s in partition if partition[s][3] > 1 or s !=m ]) / 2.0)

        ### TEST LOG ERROR TYPES #######
        # c = Counter()
        # for j in range(len(PFM)):
        #     max_v_j = max(PFM[j], key = lambda x: PFM[j][x] )
        #     for v in PFM[j]:
        #         if v != max_v_j:
        #            c[v] += PFM[j][v]
        # print("Error types:", c, "depth:", len(partition) )
        #############################

        for s in partition:
            # if minimizer_errors < partition[s][0]:
            #     nr_pos_to_correct = int( partition[s][0] - minimizer_errors ) #decide how many errors we should correct here
            # else:
            #     nr_pos_to_correct = int(math.ceil(partition[s][0] / 2.0)) #decide how many errors we should correct here
            # nr_pos_to_correct = max(int( partition[s][0] - minimizer_errors ), int(math.ceil(partition[s][0] / 2.0)))
            nr_pos_to_correct = int(math.ceil(partition[s][0] / 2.0)) #decide how many errors we should correct here

            # print("positions to correct for sequence s:", nr_pos_to_correct, s ==m)
            if nr_pos_to_correct  == 0:
                continue

            s_alignment_in_matrix = alignment_matrix[s]
            # find the position probabilities of the alignment of s in PFM

            pos_freqs_for_s = []
            for j in range(len(PFM)):
                pos_freqs_for_s.append( (j, PFM[j][s_alignment_in_matrix[j]]) )

            pos_freqs_for_s.sort(key=lambda x: x[1]) # sort with respect to smallest frequencies                    
            pos, highest_freq_of_error_to_correct = pos_freqs_for_s[ nr_pos_to_correct - 1 ]
            end_position_in_list = nr_pos_to_correct

            pp = nr_pos_to_correct
            while pos_freqs_for_s[pp][1] == highest_freq_of_error_to_correct:
                end_position_in_list += 1
                pp += 1

            J = [j for j, freq in random.sample(pos_freqs_for_s[:end_position_in_list], nr_pos_to_correct)]




            ########### TEST WEIGHTING EACH MINORITY POSITION BY IT'S OBSERVED FREQUENCY THROUGHOUT THE ALIGNMENTS TO THE MINIMIZER ################
            # pos_freqs_for_s_mod = []
            # for j in range(len(PFM)):
            #     v_j = s_alignment_in_matrix[j]
            #     pos_freqs_for_s_mod.append( (j, PFM[j][v_j] / float(max(c[v_j], 1) ) ))
            # pos_freqs_for_s_mod.sort(key=lambda x: x[1]) # sort with respect to smallest frequencies                    
            # pos, highest_freq_of_error_to_correct = pos_freqs_for_s_mod[ nr_pos_to_correct - 1 ]
            # end_position_in_list = nr_pos_to_correct
            # for pp in range(nr_pos_to_correct, len(pos_freqs_for_s_mod)):
            #     # print(pos_freqs_for_s_mod[pp][1], highest_freq_of_error_to_correct)
            #     if pos_freqs_for_s_mod[pp][1] > highest_freq_of_error_to_correct:
            #         break
            #     else:
            #         end_position_in_list += 1
            # J = [j for j, freq in random.sample(pos_freqs_for_s_mod[:end_position_in_list], nr_pos_to_correct)]
            #############################################


            # ####### TEST CHOOSING RANDOM SUBSET OUT OF ALL MINORITY POSITONS IN THE READ ################
            # minority_positions_for_s = []
            # for j in range(len(PFM)):
            #     count_v_j = PFM[j][s_alignment_in_matrix[j]]
            #     max_v_j = max(PFM[j], key = lambda x: PFM[j][x] )
            #     if count_v_j < PFM[j][max_v_j]:
            #         minority_positions_for_s.append(j)
            # # print(len(minority_positions_for_s))

            # if nr_pos_to_correct > len(minority_positions_for_s):
            #     print("OMFG!!", len(minority_positions_for_s), nr_pos_to_correct)
            #     nr_pos_to_correct = len(minority_positions_for_s)
            # J = random.sample(minority_positions_for_s, nr_pos_to_correct)
            ##############################################


            # J = [j for j, prob in pos_freqs_for_s[:nr_pos_to_correct]] # J is the set of the nr_pos_to_correct smallest position probabilities
            # print(nr_pos_to_correct, end_position_in_list)
            # print(pos_freqs_for_s[:end_position_in_list])
            # print(J)

            s_new = alignment_matrix[s]
            for j in J:
                old_nucl = s_new[j]
                highest_prob_character_at_j = max(PFM[j], key=lambda k: PFM[j][k])

                if highest_prob_character_at_j == old_nucl: # choose the other highest on if tie (should happen only when partition consist of two sequences)
                    pmf_j_minus_variant = copy.deepcopy(PFM[j])
                    del pmf_j_minus_variant[old_nucl] 
                    highest_prob_character_at_j = max(pmf_j_minus_variant, key=lambda k: pmf_j_minus_variant[k])


                # print("correcting", s_new[j], "to", highest_prob_character_at_j )
                s_new[j] = highest_prob_character_at_j
            s_modified = "".join([nucl for nucl in s_new if nucl != "-" ])

            # only unique strings can change in this step

            accession_of_s = unique_seq_to_acc[s] # this is still unique
            S_prime_partition[accession_of_s] = s_modified
    
    return S_prime_partition

