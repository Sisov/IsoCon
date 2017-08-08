from __future__ import print_function
import os
import sys
import argparse
import re
import numpy as np
import signal
from multiprocessing import Pool
import multiprocessing as mp
import math

import networkx as nx
import edlib

from modules import functions
def edlib_traceback_allow_ends(x, y, mode="NW", task="path", k=1, end_threshold = 0):
    result = edlib.align(x, y, mode=mode, task=task, k=k)
    ed = result["editDistance"]
    locations =  result["locations"]
    cigar =  result["cigar"]
    # print(cigar, ed)
    # for aln_type in cigar:
    #     print(aln_type)
        # print(aln_type, length)
    # if ed == 1:
    #     print(cigar)
    if cigar: # and len(cigar) < 15:
        tuples = []
        result = re.split(r'[=DXSMI]+', cigar)
        # print(result)
        # print(cigar)
        i = 0
        for length in result[:-1]:
            i += len(length)
            type_ = cigar[i]
            i += 1
            tuples.append((length, type_ ))
            # print(tuples)
        # print(result)
        # print(tuples)
        # print(ed, cigar)
        ed_ignore_ends = ed
        if tuples[0][1] == "D" or  tuples[0][1] == "I":
            begin_snippet = int(tuples[0][0])
            if begin_snippet <= end_threshold:
                ed_ignore_ends -= int(begin_snippet)
        if tuples[-1][1] == "D" or  tuples[-1][1] == "I":
            end_snippet = int(tuples[-1][0])
            if end_snippet <= end_threshold:
                ed_ignore_ends -= int(end_snippet)  
        # if ed > ed_ignore_ends:          
        #     print("ed global:", ed, "ed after:", ed_ignore_ends)
        ed = ed_ignore_ends

    if ed ==0:
        print("here")
        # assert False
    return ed, locations, cigar


def read_fasta(fasta_file):
    fasta_seqs = {}
    k = 0
    temp = ''
    accession = ''
    for line in fasta_file:
        if line[0] == '>' and k == 0:
            accession = line[1:].strip()
            fasta_seqs[accession] = ''
            k += 1
        elif line[0] == '>':
            yield accession, temp
            temp = ''
            accession = line[1:].strip()
        else:
            temp += line.strip()
    if accession:
        yield accession, temp


def get_minimizers_helper(arguments):
    args, kwargs = arguments
    return get_minimizers(*args, **kwargs)


def get_minimizers_under_ignored_edge_ends(seq_to_acc_list_sorted, params):
    if params.single_core:
        best_edit_distances = get_minimizers(seq_to_acc_list_sorted, 0, 0, seq_to_acc_list_sorted, params.minimizer_search_depth, params.ignore_ends_len)

        # implement check here to se that all seqs got a minimizer, if not, print which noes that did not get a minimizer computed.!

    else:
        ####### parallelize alignment #########
        # pool = Pool(processes=mp.cpu_count())
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)
        pool = Pool(processes=mp.cpu_count())

        # here we split the input into chunks
        chunk_size = max(int(len(seq_to_acc_list_sorted) / (10*mp.cpu_count())), 20 )
        ref_seq_chunks = [ ( max(0, i - params.minimizer_search_depth -1), seq_to_acc_list_sorted[max(0, i - params.minimizer_search_depth -1) : i + chunk_size + params.minimizer_search_depth +1 ]) for i in range(0, len(seq_to_acc_list_sorted), chunk_size) ]
        print([j for j, ch in ref_seq_chunks])
        print("reference chunks:", [len(ch) for j,ch in ref_seq_chunks])

        chunks = [(i, seq_to_acc_list_sorted[i:i + chunk_size]) for i in range(0, len(seq_to_acc_list_sorted), chunk_size)] 
        print([i for i,ch in chunks])
        print("query chunks:", [len(ch) for i,ch in chunks])
        # get minimizers takes thre sub containers: 
        #  chunk - a container with (sequences, accesions)-tuples to be aligned (queries)
        #  ref_seq_chunks - a container with (sequences, accesions)-tuples to be aligned to (references)
        #  already_converged_chunks - a set of query sequences that has already converged 

        try:
            res = pool.map_async(get_minimizers_helper, [ ((chunks[i][1],  chunks[i][0], chunks[i][0] - ref_seq_chunks[i][0], ref_seq_chunks[i][1], params.minimizer_search_depth, params.ignore_ends_len), {}) for i in range(len(chunks))] )
            best_edit_distances_results =res.get(999999999) # Without the timeout this blocking call ignores all signals.
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, terminating workers")
            pool.terminate()
            sys.exit()
        else:
            # print("Normal termination")
            pool.close()
        pool.join()
        best_edit_distances = {}
        for sub_graph in best_edit_distances_results:
            for seq in sub_graph:
                assert seq not in best_edit_distances
            best_edit_distances.update(sub_graph)

    return best_edit_distances


def get_invariants_under_ignored_edge_ends(seq_to_acc_list_sorted, params):
    if params.single_core:
        best_edit_distances = get_minimizers(seq_to_acc_list_sorted, 0, 0, seq_to_acc_list_sorted, params.minimizer_search_depth, params.ignore_ends_len)

        # implement check here to se that all seqs got a minimizer, if not, print which noes that did not get a minimizer computed.!

    else:
        ####### parallelize alignment #########
        # pool = Pool(processes=mp.cpu_count())
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)
        pool = Pool(processes=mp.cpu_count())

        # here we split the input into chunks
        chunk_size = max(int(len(seq_to_acc_list_sorted) / (10*mp.cpu_count())), 20 )
        ref_seq_chunks = [ ( max(0, i - params.minimizer_search_depth -1), seq_to_acc_list_sorted[max(0, i - params.minimizer_search_depth -1) : i + chunk_size + params.minimizer_search_depth +1 ]) for i in range(0, len(seq_to_acc_list_sorted), chunk_size) ]
        print([j for j, ch in ref_seq_chunks])
        print("reference chunks:", [len(ch) for j,ch in ref_seq_chunks])

        chunks = [(i, seq_to_acc_list_sorted[i:i + chunk_size]) for i in range(0, len(seq_to_acc_list_sorted), chunk_size)] 
        print([i for i,ch in chunks])
        print("query chunks:", [len(ch) for i,ch in chunks])
        # get minimizers takes thre sub containers: 
        #  chunk - a container with (sequences, accesions)-tuples to be aligned (queries)
        #  ref_seq_chunks - a container with (sequences, accesions)-tuples to be aligned to (references)
        #  already_converged_chunks - a set of query sequences that has already converged 

        try:
            res = pool.map_async(get_minimizers_helper, [ ((chunks[i][1],  chunks[i][0], chunks[i][0] - ref_seq_chunks[i][0], ref_seq_chunks[i][1], params.minimizer_search_depth, params.ignore_ends_len), {}) for i in range(len(chunks))] )
            best_edit_distances_results =res.get(999999999) # Without the timeout this blocking call ignores all signals.
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, terminating workers")
            pool.terminate()
            sys.exit()
        else:
            # print("Normal termination")
            pool.close()
        pool.join()
        best_edit_distances = {}
        for sub_graph in best_edit_distances_results:
            for seq in sub_graph:
                assert seq not in best_edit_distances
            best_edit_distances.update(sub_graph)
        
    # store only invariants here, i.e., edit distance 0 when ignoring ends!
    for acc1 in list(best_edit_distances.keys()):
        for acc2 in list(best_edit_distances[acc1].keys()):
            if best_edit_distances[acc1][acc2] != 0:
                del best_edit_distances[acc1][acc2]

    return best_edit_distances


def get_minimizers(batch_of_queries, global_index_in_matrix, start_index, seq_to_acc_list_sorted, minimizer_search_depth, ignore_ends_threshold):
    best_edit_distances = {}
    lower_target_edit_distances = {}
    print("Processing global index:" , global_index_in_matrix)
    # error_types = {"D":0, "S": 0, "I": 0}
    for i in range(start_index, start_index + len(batch_of_queries)):
        if i % 500 == 0:
            print("processing ", i)
        seq1 = seq_to_acc_list_sorted[i][0]
        acc1 = seq_to_acc_list_sorted[i][1]
        best_edit_distances[acc1] = {}

        if acc1 in lower_target_edit_distances:
            best_ed = lower_target_edit_distances[acc1] 
            # print("already_comp", best_ed )
        else:
            best_ed = len(seq1)

        stop_up = False
        stop_down = False
        j = 1
        while True:
        # for j in range(1,len(seq_to_acc_list_sorted)):
            if i - j < 0:
                stop_down = True
            if i + j >= len(seq_to_acc_list_sorted):
                stop_up = True

            if not stop_down:
                seq2 = seq_to_acc_list_sorted[i - j][0]
                acc2 = seq_to_acc_list_sorted[i - j][1]  

                if math.fabs(len(seq1) - len(seq2)) > best_ed + 2*ignore_ends_threshold:
                    stop_down = True

            if not stop_up:
                seq3 = seq_to_acc_list_sorted[i + j][0]
                acc3 = seq_to_acc_list_sorted[i + j][1]  

                if math.fabs(len(seq1) - len(seq3)) > best_ed + 2*ignore_ends_threshold:
                    stop_up = True

            if not stop_down:
                edit_distance, locations, cigar = edlib_traceback_allow_ends(seq1, seq2, mode="NW", task="path", k=best_ed+2*ignore_ends_threshold, end_threshold = ignore_ends_threshold)
                if 0 <= edit_distance < best_ed:
                    best_ed = edit_distance
                    best_edit_distances[acc1] = {}
                    best_edit_distances[acc1][acc2] = edit_distance
                elif edit_distance == best_ed:
                    best_edit_distances[acc1][acc2] = edit_distance

                if acc2 in lower_target_edit_distances:
                    if 0 < edit_distance < lower_target_edit_distances[acc2]: 
                        lower_target_edit_distances[acc2] = edit_distance 
                else:
                    if 0 < edit_distance: 
                        lower_target_edit_distances[acc2] = edit_distance 

            if not stop_up:
                edit_distance, locations, cigar = edlib_traceback_allow_ends(seq1, seq3, mode="NW", task="path", k=best_ed+2*ignore_ends_threshold, end_threshold = ignore_ends_threshold)
                if 0 <= edit_distance < best_ed:
                    best_ed = edit_distance
                    best_edit_distances[acc1] = {}
                    best_edit_distances[acc1][acc3] = edit_distance
                elif edit_distance == best_ed:
                    best_edit_distances[acc1][acc3] = edit_distance

                if acc3 in lower_target_edit_distances:
                    if 0 < edit_distance < lower_target_edit_distances[acc3]: 
                        lower_target_edit_distances[acc3] = edit_distance 
                else:
                    if 0 < edit_distance:                 
                        lower_target_edit_distances[acc3] = edit_distance 
            
            if stop_down and stop_up:
                break

            if j >= minimizer_search_depth:
                break
            j += 1
        # print(best_edit_distances[acc1])
        # print("best ed:", best_ed)
        # if best_ed > 100:
        #     print(best_ed, "for seq with length", len(seq1), seq1)
    return best_edit_distances



def partition_highest_reachable_with_edge_degrees(G_star):
    # G_star, converged = graphs.construct_exact_minimizer_graph_improved(S, params)
    unique_start_strings = set(G_star.nodes())

    print("len G_star:", len(G_star))
    partition_sizes = []
    nr_consensus = 0
    G_transpose = nx.reverse(G_star)
    print("len G_star_transposed (minimizers):", len(G_transpose))

    print(sorted([len(G_transpose.neighbors(n)) for n in G_transpose], reverse=True))
    M = {}
    partition = {}
    # print("here")
    for subgraph in sorted(nx.weakly_connected_component_subgraphs(G_transpose), key=len, reverse=True):
        print("Subgraph of size", len(subgraph.nodes()), "nr edges:", [x for x in subgraph.nodes()] )
        while subgraph:
            reachable_comp_sizes = []
            reachable_comp_weights = {}
            reachable_comp_nodes = []
            direct_neighbors = {}
            processed = set()

            biggest_reachable_comp_size = 0
            biggest_reachable_comp_weight = 0
            biggest_reachable_comp_nodes = set()
            biggest_reachable_comp_minimizer = "XXXXX"


            for m in subgraph:                
                if m in processed:
                    continue

                reachable_comp = set([m])
                reachable_comp_weight = subgraph.node[m]["degree"]
                processed.add(m)



                ####################################################
                # take all reachable nodes
                ####################################################

                for n1,n2 in nx.dfs_edges(subgraph, source=m): # store reachable node as processed here to avoid computation
                    if n2 == m:
                        continue
                    processed.add(n2)
                    reachable_comp.add(n2)
                    reachable_comp_weight += subgraph.node[n2]["degree"]
                ####################################################
                ####################################################
                

                # print("total component weight:", reachable_comp_weight)

                if biggest_reachable_comp_weight == 0:
                    biggest_reachable_comp_weight = reachable_comp_weight
                    biggest_reachable_comp_nodes = set(reachable_comp)
                    biggest_reachable_comp_size = len(reachable_comp)
                    biggest_reachable_comp_minimizer = m

                elif reachable_comp_weight >= biggest_reachable_comp_weight:
                    if reachable_comp_weight > biggest_reachable_comp_weight:
                        biggest_reachable_comp_weight = reachable_comp_weight
                        biggest_reachable_comp_nodes = set(reachable_comp)
                        biggest_reachable_comp_size = len(reachable_comp)
                        biggest_reachable_comp_minimizer = m

                    elif reachable_comp_weight == biggest_reachable_comp_weight:
                        if biggest_reachable_comp_weight > 1:
                            # print("tie both in weighted partition size and total edit distance. Choosing lexographically smaller minimizer")
                            # print(" weighted partition size:", biggest_reachable_comp_weight, " total edit distance:", edit_distances_to_m[m])
                            pass
                        
                        if m < biggest_reachable_comp_minimizer:
                            biggest_reachable_comp_nodes = set(reachable_comp)
                            biggest_reachable_comp_minimizer = m
                        else:
                            pass

                    else:
                        print("BUG!")

            if biggest_reachable_comp_weight == 0: # if there were no edges! partition is minimizer itself
                M[m] = 0 
                partition[m] = set()
            else:
                minimizer = biggest_reachable_comp_minimizer # "XXXXXX" #biggest_reachable_comp_minimizer #
                max_direct_weight = 0
                # print("total nodes searched in this pass:", len(biggest_reachable_comp_nodes))
                for n in biggest_reachable_comp_nodes:
                    direct_weight = subgraph.node[n]["degree"]                    
                    direct_weight += len(subgraph.neighbors(n))

                    if direct_weight > max_direct_weight:
                        max_direct_weight = direct_weight
                        minimizer = n
                    elif direct_weight == max_direct_weight:
                        minimizer = min(minimizer, n)
                # print("minimizer direct weight:", max_direct_weight, "nodes in reachable:", len(biggest_reachable_comp_nodes))
                M[minimizer] = biggest_reachable_comp_weight   
                partition[minimizer] = biggest_reachable_comp_nodes.difference(set([minimizer]))
                assert minimizer in biggest_reachable_comp_nodes

            subgraph.remove_nodes_from(biggest_reachable_comp_nodes)
            nr_consensus += 1

    print("NR CONSENSUS:", nr_consensus)
    print("NR minimizers:", len(M), len(partition))
    print("partition sizes(identical strings counted once): ", sorted([len(partition[p]) +1 for p in  partition], reverse = True))

    total_strings_in_partition = sum([ len(partition[p]) +1 for p in  partition])
    partition_sequences = set()
    for m in partition:
        partition_sequences.add(m)
        # print("partition size:", len(partition[m]))
        # print(len(m))
        for s in partition[m]:
            partition_sequences.add(s)

    assert unique_start_strings == partition_sequences
    assert total_strings_in_partition == len(unique_start_strings)

    return G_star, partition, M


def get_minimizers_graph_transposed_under_ignored_ends(candidate_transcripts, args):
    seq_to_acc = {seq: acc for (acc, seq) in candidate_transcripts.items()}
    seq_to_acc_list = list(seq_to_acc.items())
    seq_to_acc_list_sorted = sorted(seq_to_acc_list, key= lambda x: len(x[0]))
    minimizer_graph = get_minimizers_under_ignored_edge_ends(seq_to_acc_list_sorted, args)

    for acc1 in list(minimizer_graph.keys()):
        for acc2 in list(minimizer_graph[acc1].keys()):
            ed = minimizer_graph[acc1][acc2]
            if ed > 10:
                del minimizer_graph[acc1][acc2]
                print("had ed > 10 statistocal test", acc1, acc2)


    no_ref_to_test_to = set()
    for acc1 in  minimizer_graph:
        seq1 = candidate_transcripts[acc1]
        
        if len(minimizer_graph[acc1]) == 0: # all isolated nodes in this graph
            no_ref_to_test_to.add(acc1)

        for acc2 in minimizer_graph[acc1]:
            seq2 = candidate_transcripts[acc2]
            if minimizer_graph[acc1][acc2] > 0:
                print(acc1, acc2,  minimizer_graph[acc1][acc2])
    
    minimizer_graph_transposed = functions.transpose(minimizer_graph)

    # isolated_nodes = set(candidate_transcripts.keys()) -  set(minimizer_graph_transposed)
    # print("isolated:",isolated_nodes )
    # for c_isolated in isolated_nodes:
    #     minimizer_graph_transposed[c_isolated] = {}
    print("isolated:", no_ref_to_test_to)
    for c_isolated in no_ref_to_test_to:
        minimizer_graph_transposed[c_isolated] = {}

    return minimizer_graph_transposed

def collapse_candidates_under_ends_invariant(candidate_transcripts, candidate_support, args):
    print("candidates before edge invariants:", len(candidate_transcripts))

    seq_to_acc = {seq: acc for (acc, seq) in candidate_transcripts.items()}
    seq_to_acc_list = list(seq_to_acc.items())
    seq_to_acc_list_sorted = sorted(seq_to_acc_list, key= lambda x: len(x[0]))
    invariant_graph = get_invariants_under_ignored_edge_ends(seq_to_acc_list_sorted, args)
    # convert minimizer graph to nx graph object
    G = nx.DiGraph()
    # add nodes
    for acc in candidate_transcripts:
        deg = candidate_support[acc]
        G.add_node(acc, degree = deg)
    # add edges
    for acc1 in  invariant_graph:
        for acc2 in invariant_graph[acc1]:
            G.add_edge(acc1, acc2)
    G_star, partition, M = partition_highest_reachable_with_edge_degrees(G)

    for t in partition:
        print(t, partition[t])
    print("candidates after edge invariants:", len(partition))
    return partition

def main(args):
    candidate_transcripts = {acc: seq for (acc, seq) in  read_fasta(open(args.candidate_transcripts, 'r'))}
    candidate_support = {}
    for (acc, seq) in  read_fasta(open(args.candidate_transcripts, 'r')):
        supp = acc.split("_support_")[1]
        candidate_support[acc] = int(supp)
    
    print("Number of consensus:", len(candidate_transcripts))
    seq_to_acc = {seq: acc for (acc, seq) in  read_fasta(open(args.candidate_transcripts, 'r'))}
    seq_to_acc_list = list(seq_to_acc.items())
    seq_to_acc_list_sorted = sorted(seq_to_acc_list, key= lambda x: len(x[0]))
    collapsed_candidate_transcripts =  { acc : seq for (seq, acc) in  seq_to_acc.items() }
    print("Number of collapsed consensus:", len(collapsed_candidate_transcripts))
    assert len(collapsed_candidate_transcripts) == len(candidate_transcripts) # all transcripts should be unique at this point
    

    minimizer_graph = get_invariants_under_ignored_edge_ends(seq_to_acc_list_sorted, args)

    outfile = open(args.outfile, "w")
    edges = 0
    tot_ed = 0
    for acc1 in  minimizer_graph:
        seq1 = candidate_transcripts[acc1]
        for acc2 in minimizer_graph[acc1]:
            seq2 = candidate_transcripts[acc2]
            edges += 1
            tot_ed += minimizer_graph[acc1][acc2]
            outfile.write("{0}\t{1}\t{2}\t{3}\t{4}\n".format(acc1, candidate_support[acc1], acc2, candidate_support[acc2],  minimizer_graph[acc1][acc2]))

    print("Number of edges:", edges)
    print("Total edit distance:", tot_ed)
    if float(edges) > 0:
        print("Avg ed (ed/edges):", tot_ed/ float(edges))

    # convert minimizer graph to nx graph object
    G = nx.DiGraph()
    # add nodes
    for acc in candidate_transcripts:
        deg = candidate_support[acc]
        G.add_node(acc, degree = deg)
    # add edges
    for acc1 in  minimizer_graph:
        for acc2 in minimizer_graph[acc1]:
            G.add_edge(acc1, acc2)
    G_star, partition, M = partition_highest_reachable_with_edge_degrees(G)

    print("candidates after edge invariants:", len(partition))
    # for t in partition:
    #     print(t)
    #     print(partition[t])
    #     print()




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Print minimizer graph allowing for mismatches in ends.")
    parser.add_argument('candidate_transcripts', type=str, help='Path to the consensus fasta file')
    parser.add_argument('outfile', type=str, help='Outfile of results')
    parser.add_argument('--ignore_ends_len', type=int, default=15, help='Number of bp to ignore in ends. If two candidates are identical expept in ends of this size, they are collapses and the longest common substing is chosen to represent them. In statistical test step, minimizers are found based on ignoring the ends of this size. Also indels in ends will not be tested. [default ignore_ends_len=15].')
    parser.add_argument('--single_core', dest='single_core', action='store_true', help='Force working on single core. ')
    parser.add_argument('--minimizer_search_depth', type=int, default=2**32, help='Maximum number of pairwise alignments in search matrix to find minimizer. [default =2**32]')

    args = parser.parse_args()

    main(args)
