"""
    PFM is a list of dicts, where the inner dicts are one per column in the PFM matrix, its keys by characters A, C, G, T, -
    alignment_matrix is a representation of all alignments in a partition. this is a dictionary where sequences s_i belonging to the 
    partition as keys and the alignment of s_i with respectt to the alignment matix.
"""
import os
import unittest

import copy
from time import time
import re

from modules.functions import transpose,create_position_probability_matrix
from modules.partitions import highest_reachable_with_edge_degrees
from modules.SW_alignment_module import sw_align_sequences, sw_align_sequences_keeping_accession
from modules.edlib_alignment_module import edlib_align_sequences, edlib_align_sequences_keeping_accession
from modules.input_output import fasta_parser, write_output
from modules import correct_sequence_to_minimizer
from collections import defaultdict

# def get_homopolymer_invariants(candidate_transcripts):
#     seq_to_acc = { seq : acc for (acc, seq) in  candidate_transcripts.items() }
#     print("Unique before compression: ", len(seq_to_acc) )

#     candidate_transcripts_transformed = {}
#     clusters = defaultdict(list)
#     for acc in candidate_transcripts:
#         seq_transformed = transform(candidate_transcripts[acc])
#         candidate_transcripts_transformed[acc] = seq_transformed
#         clusters[seq_transformed].append(acc)

#     seq_to_acc_transformed = { seq : acc for (acc, seq) in candidate_transcripts_transformed.items()}
#     print("Unique after compression: ", len(seq_to_acc_transformed) )

#     edges = {}
#     for seq in clusters:
#         if len(clusters[seq]) > 1:
#             # print(clusters[seq])
#             for acc in clusters[seq]:
#                 edges[acc] = {}
#             for acc1, acc2 in combinations(clusters[seq], 2):
#                 edges[acc1][acc2] = 1
#                 edges[acc2][acc1] = 1

#     return edges


# #############################################################
# #############################################################
# if homopolymer_compression:
#     # All converged
#     for acc, s in S.items():
#         if s not in G_star:
#             G_star[s] = {}
#         else:
#             if s in G_star[s]:
#                 G_star[s][s] += 1  
#                 # print(acc)
#             else:
#                 G_star[s][s] = 2
#                 # print(acc)

#     converged = False
#     print("ENTERING HOMOPOLYMER COMPRESSION MODE")
#     # create homopolymer equivalence class edges
#     G_homopolymer_star = {}
#     weight = {}
#     for acc, s in S.items():
#         if s not in G_star:
#             G_star[s] = {}
#             weight[s] = 1
#         else:
#             weight[s] += 1

#     homopolymer_edges = get_homopolymer_invariants(S)
#     homopol_extra_added = 0
#     for acc1 in homopolymer_edges:
#         s1 = S[acc1]
#         for acc2 in homopolymer_edges[acc1]:
#             # Do individual minimizer component graphs of the homopolymenr equivalence classes here!
#             s2 = S[acc2]
#             G_star[s1][s2] = 1
#             G_star[s2][s1] = 1
#             homopol_extra_added += 2

#     print("EDGES FROM HOMOPOLYMER IDENTICAL:", homopol_extra_added)
#     unique_strings = {transform(seq) : acc for acc, seq in S.items()}
#     S_prime_transformed = {acc : seq for seq, acc in unique_strings.items()}
#     # Send homopolymer components to this function!
#     # Keep in mind. Isolated nodes are not neccesarily isolated!
#     all_internode_edges_in_minimizer_graph, isolated_nodes = minimizer_graph.compute_minimizer_graph(S_prime_transformed, params) # send in a list of nodes that already has converged, hence avoid unnnecessary computation

#     #############################################################
#     #############################################################

def get_unique_seq_accessions(S):
    seq_to_acc = {}
    for acc, seq in  S.items():
        if seq in seq_to_acc:
            seq_to_acc[seq].append(acc)
        else: 
            seq_to_acc[seq] = []
            seq_to_acc[seq] = [acc]

    unique_seq_to_acc = {seq: acc_list[0] for seq, acc_list in  seq_to_acc.items() if len(acc_list) == 1 } 
    print("Unique seqs left:", len(unique_seq_to_acc))

    return seq_to_acc

def get_partition_alignments(graph_partition, M, G_star):
    exact_edit_distances = edlib_align_sequences(graph_partition, single_core = False)    
        
    ed_temp = [ exact_edit_distances[s1][s2] for s1 in exact_edit_distances for s2 in exact_edit_distances[s1]  ] 
    ed_temp.sort()
    print("ED from edlib:", ed_temp)
    print("number of ed calculated:", len(ed_temp))

    exact_alignments = sw_align_sequences(exact_edit_distances, single_core = False)

    ssw_temp = [ exact_alignments[s1][s2] for s1 in exact_alignments for s2 in exact_alignments[s1]  ] 
    # ssw_temp.sort()
    print("Number of alignments returned from SSW:", len(ssw_temp))
    print("Number of alignments that were removed before correction phase -- too many mismatchas in ends (#ED-alignments - # SSW-alignments): {0} ".format(  len(ed_temp) - len(ssw_temp) ))

    pattern = r"[-]{20,}"
    for s1 in exact_alignments.keys(): 
        for s2 in exact_alignments[s1].keys():
            s1_alignment, s2_alignment, (matches, mismatches, indels) = exact_alignments[s1][s2]
            missing_exon_s1 = re.search(pattern, s1_alignment)
            missing_exon_s2 = re.search(pattern, s2_alignment)
            if missing_exon_s1:
                # print(missing_exon_s1.group(0))
                # print(s1)
                # print(s2)
                # print(len(exact_alignments[s1].keys()))
                del exact_alignments[s1][s2]
            elif missing_exon_s2:
                # print(missing_exon_s2.group(0))
                # print(s1)
                # print(s2)
                # print(len(exact_alignments[s1].keys()))
                del exact_alignments[s1][s2]

    ssw_after_exon_temp = [ exact_alignments[s1][s2] for s1 in exact_alignments for s2 in exact_alignments[s1]  ] 
    print("Number of alignments that were removed before correction phase due to exon difference larger than 20bp: {0} ".format(  len(ssw_temp) - len(ssw_after_exon_temp) ))
    # sys.exit()


    partition_alignments = {} 
    for m in M:
        # selfdegree = 1 if m not in G_star[m] else G_star[m][m]
        selfdegree = G_star.node[m]["degree"]
        partition_alignments[m] = { m : (0, m, m, selfdegree) }
        if m not in exact_alignments:
            # print("Minimizer did not have any anlignments, length:", M[m], "self-degree:", selfdegree)
            continue
        else:
            for s in exact_alignments[m]:
                aln_m, aln_s, (matches, mismatches, indels) = exact_alignments[m][s]
                edit_dist = mismatches + indels
                # indegree =  1 if s not in G_star[m] else G_star[m][s]
                # if indegree > 1:
                #     print("Larger than 1!!", indegree)
                partition_alignments[m][s] = (edit_dist, aln_m, aln_s, 1)

    print("NR candidates :", len(partition_alignments))
    return partition_alignments



def find_candidate_transcripts(read_file, params):
    """
        input: a string pointing to a fasta file
        output: a string containing a path to a fasta formatted file with consensus_id_support as accession 
                    and the sequence as the read
    """ 
    S = {acc: seq for (acc, seq) in  fasta_parser.read_fasta(open(read_file, 'r'))}

    lenghts = [len(seq) for seq in S.values()]
    print(sorted(lenghts))
    max_len = max(lenghts)
    min_len = min(lenghts)
    print("Max transcript length:{0}, Min transcript length:{1}".format(max_len, min_len))

    seq_to_acc = get_unique_seq_accessions(S)

    minimizer_start = time() 
    G_star, graph_partition, M, converged = highest_reachable_with_edge_degrees(S, params)
    partition_alignments = get_partition_alignments(graph_partition, M, G_star)       

    minimizer_elapsed = time() - minimizer_start
    write_output.logger('Time for minimizers and partition, step 1:{0}'.format(str(minimizer_elapsed)), params.logfile)

    step = 1
    prev_edit_distances_2steps_ago = [2**28,2**28,2**28] # prevents 2-cycles
    prev_edit_distances = [2**28]

    # homopolymer_mode = False

    while not converged:
        correction_start = time() 

        print("candidates:", len(M))
        edit_distances = [ partition_alignments[s1][s2][0] for s1 in partition_alignments for s2 in partition_alignments[s1]  ] 
        edit_distances.sort()
        print("edit distances from SSW:", edit_distances) 

        #################################################
        ###### temp check for isoform collapse###########
        # import re
        # pattern = r"[-]{20,}"
        # cccntr = 0
        # out_file = open(os.path.join(params.outfolder, "exon_difs.fa"), "w")
        # if params.barcodes:
        #     for s1, s1_dict in list(partition_alignments.items()): 
        #         part_size = sum([s1_dict[s_2][3] for s_2 in s1_dict])
        #         for s2, alignment_tuple in list(s1_dict.items()):
        #             if re.search(pattern, alignment_tuple[1][20: -20]) or re.search(pattern, alignment_tuple[2][20: -20]): # [20: -20] --> ignore this if-statement if missing or truncated barcode
        #                 # del partition_alignments[s1][s2]
        #                 print("Exon diff on >=20bp:", len(s2)," minimizer length:", len(s1), "length alignment:", len(alignment_tuple[2]), "edit distance:", alignment_tuple[0], "in partition of size:", part_size)
        #                 cccntr += 1
        #                 out_file.write(">{0}\n{1}\n".format(seq_to_acc[s2],s2))
        # else:
        #     for s1, s1_dict in list(partition_alignments.items()): 
        #         part_size = sum([s1_dict[s_2][3] for s_2 in s1_dict])
        #         for s2, alignment_tuple in list(s1_dict.items()):
        #             if re.search(pattern, alignment_tuple[1]) or  re.search(pattern, alignment_tuple[2]):
        #                 # del partition_alignments[s1][s2]
        #                 print("Exon diff on >=20bp:", len(s2)," minimizer length:", len(s1), "length alignment:", len(alignment_tuple[2]), "edit distance:", alignment_tuple[0], "in partition of size:", part_size)
        #                 cccntr += 1        
        #                 out_file.write(">{0}\n{1}\n".format(seq_to_acc[s2],s2))

        # print("Number of alignments containing exon difference in this pass:", cccntr)
        # sys.exit()
        ########################################################


        ###### Different convergence criterion #########

        if prev_edit_distances_2steps_ago == edit_distances:
            # Only cyclic alignments are left, these are reads that jump between two optimal alignment of two different
            # target sequeneces. This is a product of our fast heurustics of defining a minmap score + SSW filtering to choose best alignment
            print("CYCLE!!!")
            assert len(partition_alignments) == len(M)
            break
            # if homopolymer_mode:
            #     break
            # else:
            #     homopolymer_mode = True

        if sum(edit_distances) > sum(prev_edit_distances) and  max(edit_distances) > max(prev_edit_distances) :
            #return here if there is some sequence alternating between best alignments and gets corrected and re-corrected to different candidate sequences
            assert len(partition_alignments) == len(M)
            print("exiting here!")
            break
            # if homopolymer_mode:
            #     print("exiting here!")
            #     break            
            # else:
            #     homopolymer_mode = True


        has_converged = [True if ed == 0 else False for ed in edit_distances] 
        if all(has_converged):
            # we return here if tha data set contain isolated nodes.
            assert len(partition_alignments) == len(M)
            print("Normal convergence")
            break
            # if homopolymer_mode:
            #     print("Normal convergence")
            #     break
            # else: 
            #     homopolymer_mode = True
        #######################################################


        # TODO: Parallelize this part over partitions: sent in the partition and return a dict s_acc : modified string
        S_prime = correct_sequence_to_minimizer.correct_strings(partition_alignments, seq_to_acc, step, single_core = params.single_core)
        # sys.exit()

        for acc, s_prime in S_prime.items():
            S[acc] = s_prime

        print("Tot seqs:", len(S))
        seq_to_acc = get_unique_seq_accessions(S)
        # partition_alignments, partition, M, converged = partition_strings(S)

        G_star, graph_partition, M, converged = highest_reachable_with_edge_degrees(S, params)
        partition_alignments = get_partition_alignments(graph_partition, M, G_star)  
        out_file_name = os.path.join(params.outfolder, "candidates_step_" +  str(step) + ".fa")
        out_file = open(out_file_name, "w")
        for i, m in enumerate(partition_alignments):
            N_t = sum([container_tuple[3] for s, container_tuple in partition_alignments[m].items()])
            out_file.write(">{0}\n{1}\n".format("read" + str(i)+ "_support_" + str(N_t) , m))

        step += 1
        prev_edit_distances_2steps_ago = prev_edit_distances
        prev_edit_distances = edit_distances

        correction_elapsed = time() - correction_start
        write_output.logger('Time for correction, minimizers and partition, step {0}:{1}'.format(step, str(correction_elapsed)), params.logfile)
        
        # sys.exit()
   
    C = {}
    for m in M:
        N_t = partition_alignments[m][m][3] #sum([container_tuple[3] for s, container_tuple in partition_alignments[m].items()])
        if N_t > 1: # has converged to a consensus
            C[m] = N_t   


    original_reads = {acc: seq for (acc, seq) in  fasta_parser.read_fasta(open(read_file, 'r'))}
    original_reads_seq_to_accs =  defaultdict(list)
    for (acc, seq) in original_reads.items():
        original_reads_seq_to_accs[seq].append(acc)
    # original_reads_seq_to_acc = { seq : acc for (acc, seq) in  fasta_parser.read_fasta(open(read_file, 'r'))}
    reads_to_minimizers = {}
    # [for m, partition in partition_alignments.items() for s in partition]

    not_converged_reads = open(os.path.join(params.outfolder, "not_converged.fa"), "w")
    not_converged = set()
    for read_acc, seq in original_reads.items():
        corrected_s = S[read_acc]
        if corrected_s in C:
            # if corrected_s in original_reads_seq_to_accs:
            #     if C[corrected_s] >= params.min_candidate_support:
            #         reads_to_minimizers[read_acc] = { corrected_s : (original_reads[read_acc], corrected_s)}
            #     else:
            #         print("Minimizer did not pass threshold. It had support of {0} reads. And is identical to its starting seq (i.e., not corrected)".format(C[corrected_s]))
            #         print(read_acc)
            #         del C[corrected_s]
            #         not_converged_reads.write(">{0}\n{1}\n".format(read_acc, seq))
            #         not_converged.add(read_acc)

            # else:
            #     if C[corrected_s] >= params.min_candidate_support:
            #         reads_to_minimizers[read_acc] = { corrected_s : (original_reads[read_acc], corrected_s)}
            #     else:
            #         print("Read was corrected but did not pass threshold. It had support of {0} reads.".format(C[corrected_s]))
            #         print(read_acc)
            #         not_converged_reads.write(">{0}\n{1}\n".format(read_acc, seq))
            #         not_converged.add(read_acc)
            #         del C[corrected_s]
            if C[corrected_s] >= params.min_candidate_support:
                reads_to_minimizers[read_acc] = { corrected_s : (original_reads[read_acc], corrected_s)}
            else:
                print("Minimizer did not pass threshold. It had support of {0} reads.".format(C[corrected_s]))
                print(read_acc)
                del C[corrected_s]
        else:
            if corrected_s in original_reads_seq_to_accs:
                print("Read neither converged nor was it corrected (local pair r1 <---> r2 minimizer or a isolated alignment with exon difference filtered out before each correction)")
                print(read_acc)
                not_converged_reads.write(">{0}_not_corrected_not_converged\n{1}\n".format(read_acc, seq))
                not_converged.add(read_acc)

            else: # partially corrected but not converged
                not_converged_reads.write(">{0}\n{1}\n".format(read_acc, seq))
                not_converged.add(read_acc)
                print("Read partially corrected but not converged")
                print(read_acc)
                not_converged_reads.write(">{0}_corrected_but_not_converged_version\n{1}\n".format(read_acc, corrected_s))


    edit_distances_of_x_to_m = edlib_align_sequences_keeping_accession(reads_to_minimizers)
    alignments_of_x_to_m = sw_align_sequences_keeping_accession(edit_distances_of_x_to_m)

    alignments_of_x_to_m_filtered, m_to_acc, C_filtered, partition_of_X = filter_candidates(alignments_of_x_to_m, C, params)
    candidates_file_name = os.path.join(params.outfolder, "candidates_converged.fa")
    write_output.print_candidates_from_minimizers(candidates_file_name, C_filtered, m_to_acc, params)

    to_realign = {}
    for acc, seq in original_reads.items():
        if acc not in alignments_of_x_to_m_filtered:
            if acc not in not_converged:
                to_realign[acc] = seq

    return candidates_file_name, partition_of_X, to_realign 

def filter_candidates(alignments_of_x_to_c, C, params):
    alignments_of_x_to_c_transposed = transpose(alignments_of_x_to_c)   

    m_to_acc = {}

    for i, (m, support) in enumerate(list(C.items())):
        m_acc = "read_" + str(i) + "_support_" + str(support)
        m_to_acc[m] = m_acc
        
        #require support from at least 4 reads if not tested (consensus transcript had no close neighbors)
        # add extra constraint that the candidate has to have majority on _each_ position in c here otherwise most likely error
        if support >= params.min_candidate_support:
            if params.prefilter_candidates:
                # print("needs to be consensus over each base pair")
                partition_alignments_c = {m : (0, m, m, 1)}  # format: (edit_dist, aln_c, aln_x, 1)
                for x_acc in alignments_of_x_to_c_transposed[m]:
                    aln_x, aln_m, (matches, mismatches, indels) = alignments_of_x_to_c_transposed[m][x_acc]
                    ed = mismatches + indels
                    partition_alignments_c[x_acc] = (ed, aln_m, aln_x, 1) 
                    # print(ed, aln_x, aln_m)

                alignment_matrix_to_c, PFM_to_c = create_position_probability_matrix(m, partition_alignments_c)
                c_alignment = alignment_matrix_to_c[m]
                is_consensus = True
                for j in range(len(PFM_to_c)):
                    c_v =  c_alignment[j]
                    candidate_count = PFM_to_c[j][c_v]
                    max_v_j = max(PFM_to_c[j], key = lambda x: PFM_to_c[j][x] )
                    max_count = PFM_to_c[j][max_v_j]
                    if candidate_count < max_count:
                        print("not consensus at:", j)
                        is_consensus = False                    

                    # for v in PFM_to_c[j]:
                    #     if v != c_v and candidate_count <= PFM_to_c[j][v]: # needs to have at least one more in support than the second best as we have added c itself to the multialignment
                    #         print("not consensus at:", j)
                    #         is_consensus = False

                if not is_consensus:
                    print("Read with support {0} were not consensus".format(str(support)))
                    del alignments_of_x_to_c_transposed[m]
                    del C[m]
        else:
            print("deleting:")
            del alignments_of_x_to_c_transposed[m]
            del C[m]

    partition_of_X = { m_to_acc[c] : set(alignments_of_x_to_c_transposed[c].keys()) for c in  alignments_of_x_to_c_transposed}

    # we now have an accession of minimizer, change to this accession insetad of storing sequence
    alignments_of_x_to_m_filtered = transpose(alignments_of_x_to_c_transposed)
    for x_acc in list(alignments_of_x_to_m_filtered.keys()):
        for m in list(alignments_of_x_to_m_filtered[x_acc].keys()):
            m_acc = m_to_acc[m]
            aln_x, aln_m, (matches, mismatches, indels) = alignments_of_x_to_m_filtered[x_acc][m]
            del alignments_of_x_to_m_filtered[x_acc][m]
            ed =  mismatches + indels
            alignments_of_x_to_m_filtered[x_acc][m_acc] = (ed, aln_x, aln_m)

    return alignments_of_x_to_m_filtered, m_to_acc, C, partition_of_X





if __name__ == '__main__':
    unittest.main()