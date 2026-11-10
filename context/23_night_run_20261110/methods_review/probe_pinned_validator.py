#!/usr/bin/env python3
"""Execute the pinned checker in memory on isolated, explicit mutations.

This is a validator coverage probe, separate from independent_review.py.
No live methods/ reads and no author main/network repair; all save() is captured.
"""
import ast
import collections
import copy
import hashlib
import json
import math
import sys

sys.dont_write_bytecode = True
import independent_review as review


class FrozenPath:
    def __init__(self, path):
        self.path = path

    def __truediv__(self, other):
        return FrozenPath('/'.join(filter(None, [self.path, other])))

    def read_text(self):
        return review.blob(self.path).decode('utf-8')

    def read_bytes(self):
        return review.blob(self.path)


def run(mutation):
    outputs = {}
    tree = ast.parse(review.blob('analyze_pinned.py'))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    main_code = compile(ast.Module(body=[main], type_ignores=[]), 'PINNED:analyze_pinned.py', 'exec')

    def rows(path):
        data = review.rows(path.path)
        # Always fresh rows; the pinned source bytes/hash checks remain untouched.
        if mutation == 'drop_positive_capacity_row' and path.path.endswith('/model/capacity.csv'):
            victim = next(r for r in data if r['profile'] == 'ROUTE_INPUTS_UPPER_100'
                          and r['network'] == 'H_UFA_8' and r['scenario'] == 'base'
                          and float(r['occupied']) > 0)
            data.remove(victim)
        if mutation == 'shift_comparison_flight_cost' and path.path.endswith('/21_team_proposals/comparison.csv'):
            victim = next(r for r in data if r['network'] == 'H_UFA_8' and r['scenario'] == 'base')
            victim['flight_variable_cost'] = str(float(victim['flight_variable_cost']) + 1000000)
            victim['contribution_before_base_fleet_opportunity'] = str(float(victim['contribution_before_base_fleet_opportunity']) - 1000000)
        return data

    namespace = dict(ast=ast, collections=collections, hashlib=hashlib, json=json, math=math,
                     ROOT=FrozenPath(''), INPUT=FrozenPath('inputs/set001'),
                     rows=rows, save=lambda name, data: outputs.update({name: copy.deepcopy(data)}))
    exec(main_code, namespace)
    namespace['main']()
    assert outputs['checks.json']['status'] == 'PASS_SCOPED'
    return dict(mutation=mutation, result=outputs['checks.json'],
                full_author_pipeline_executed=False, source_blobs_mutated=False,
                mutation_layer='IN_MEMORY_CSV_READER_AFTER_PINNED_HASH_CHECK',
                interpretation='Hashes establish immutable bytes, not completeness/cost conservation of arbitrary inputs. This probes semantic assertions only.')


def main():
    results = [run(name) for name in ['none', 'drop_positive_capacity_row', 'shift_comparison_flight_cost']]
    review.dump('validator_probes.json', dict(source_commit=review.PIN, probes=results,
                  finding='Semantic capacity completeness and independent flight-cost bridge are absent; unchanged pinned rows independently passed the stronger reviewer checks.'))


if __name__ == '__main__':
    main()
