"""
论文A Step 1-2: 句法特征提取 + 效度检验
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
np.random.seed(SEED)

RESULT_DIR = "results/optimization/paperA"
os.makedirs(RESULT_DIR, exist_ok=True)


def save_json(data, name):
    with open(os.path.join(RESULT_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def step1_extract_syntactic_features():
    """Step 1: spaCy句法特征提取"""
    import spacy
    print("=" * 60)
    print("Step 1: spaCy句法特征提取")
    print("=" * 60)

    print("加载spaCy模型...")
    nlp = spacy.load('en_core_web_sm')

    # 加载论文B准备好的数据（已去重）
    df = pd.read_parquet('results/optimization/paperB/prepared_data.parquet')
    df = df.drop_duplicates(subset=['task_id']).reset_index(drop=True)
    print(f"样本数: {len(df)}")

    DECLARATIVE_VERBS = {'check', 'verify', 'confirm', 'test', 'validate', 'ensure'}
    TEMPORAL_MARKERS = {'then', 'next', 'after', 'before', 'finally', 'first', 'second', 'third', 'subsequently'}

    features_list = []
    instructions = df['instruction'].fillna('').tolist()
    batch_size = 500

    print(f"处理 {len(instructions)} 条指令（每批{batch_size}）...")
    for batch_start in range(0, len(instructions), batch_size):
        batch_end = min(batch_start + batch_size, len(instructions))
        if batch_start % 5000 == 0:
            print(f"  进度: {batch_start}/{len(instructions)}")

        batch_texts = [str(t)[:500] if t else "" for t in instructions[batch_start:batch_end]]
        docs = list(nlp.pipe(batch_texts, disable=['ner']))

        for i, doc in enumerate(docs):
            idx = batch_start + i
            n_tokens = max(len(doc), 1)

            # 1. 祈使句谓语动词数（ROOT节点且POS=VERB）
            imperative_verbs = sum(1 for t in doc if t.dep_ == 'ROOT' and t.pos_ == 'VERB')

            # 2-3. 情态标记
            modal_obligation = 0
            modal_prohibition = 0
            for t in doc:
                if t.dep_ == 'aux' and t.lemma_ in {'must', 'should', 'need', 'have'}:
                    modal_obligation += 1
                if t.dep_ == 'neg':
                    modal_prohibition += 1

            # 4. 宣告性谓语
            declarative_pred = sum(1 for t in doc if t.lemma_ in DECLARATIVE_VERBS)

            # 5. 完成体标记
            perfective = sum(1 for t in doc if t.tag_ == 'VBN' and t.head.lemma_ in {'have', 'has', 'had', 'be', 'been'})

            # 6. 篇章时序连接词
            discourse_temporal = sum(1 for t in doc if t.lemma_ in TEMPORAL_MARKERS)

            # 7. 论元结构（直接宾语/介词宾语数量）
            object_args = sum(1 for t in doc if t.dep_ in {'dobj', 'pobj', 'obj'})

            # 8-10. 句法复杂性
            # T单位近似：每个ROOT或主句谓语算一个T单位
            t_units = max(sum(1 for t in doc if t.dep_ == 'ROOT'), 1)
            clauses = sum(1 for t in doc if t.dep_ in {'ROOT', 'advcl', 'csubj', 'ccomp', 'xcomp', 'relcl'})
            clause_density = clauses / t_units

            # 依存树深度
            depths = []
            for token in doc:
                depth = 0
                current = token
                while current.head != current:
                    depth += 1
                    current = current.head
                    if depth > 30:
                        break
                depths.append(depth)
            dep_depth = max(depths) if depths else 0

            # 11. 名词实体数（简单计数专有名词）
            noun_entities = sum(1 for t in doc if t.pos_ == 'PROPN')

            features_list.append({
                'task_id': df.iloc[idx]['task_id'],
                'imperative_verb_count': imperative_verbs,
                'modal_obligation_count': modal_obligation,
                'modal_prohibition_count': modal_prohibition,
                'declarative_predicate_count': declarative_pred,
                'perfective_aspect_count': perfective,
                'discourse_temporal_count': discourse_temporal,
                'object_argument_count': object_args,
                't_unit_count': t_units,
                'clause_density': clause_density,
                'dependency_tree_depth': dep_depth,
                'noun_entity_count': noun_entities,
            })

    feat_df = pd.DataFrame(features_list)
    feat_df.to_parquet(os.path.join(RESULT_DIR, '01_syntactic_features.parquet'))

    # 描述统计
    feature_cols = [c for c in feat_df.columns if c != 'task_id']
    desc = {}
    for c in feature_cols:
        desc[c] = {
            'mean': float(feat_df[c].mean()),
            'std': float(feat_df[c].std()),
            'median': float(feat_df[c].median()),
            'min': float(feat_df[c].min()),
            'max': float(feat_df[c].max()),
            'pct_nonzero': float((feat_df[c] > 0).mean()),
        }

    report = {
        'n_samples': len(feat_df),
        'n_features': len(feature_cols),
        'feature_descriptives': desc,
        'extraction_method': 'spaCy en_core_web_sm',
    }
    save_json(report, '01_feature_extraction_report')
    print(f"\n特征提取完成: {len(feat_df)}样本 × {len(feature_cols)}特征")
    for c in feature_cols:
        print(f"  {c}: mean={desc[c]['mean']:.3f}, nonzero={desc[c]['pct_nonzero']:.1%}")

    return df, feat_df


def step2_validity_check(df, feat_df):
    """Step 2: 效度检验"""
    print("\n" + "=" * 60)
    print("Step 2: 效度检验")
    print("=" * 60)

    merged = df.merge(feat_df, on='task_id', how='inner')

    # 聚合效度：新句法特征 vs 原关键词特征
    convergent_pairs = [
        ('imperative_verb_count', 'has_target_action', '应正相关'),
        ('declarative_predicate_count', 'has_completion_criteria', '应正相关'),
        ('modal_obligation_count', 'has_constraint_words', '应正相关'),
        ('modal_prohibition_count', 'has_constraint_words', '应正相关'),
        ('discourse_temporal_count', 'has_operation_order', '应正相关'),
        ('object_argument_count', 'has_operation_object', '应正相关'),
        ('modal_obligation_count', 'modal_prohibition_count', '应正相关（同类特征）'),
    ]

    discriminant_pairs = [
        ('perfective_aspect_count', 'modal_obligation_count', '应低相关'),
        ('dependency_tree_depth', 'declarative_predicate_count', '应低相关'),
        ('noun_entity_count', 'discourse_temporal_count', '应低相关'),
    ]

    convergent = {}
    print("\n-- 聚合效度 --")
    for v1, v2, expectation in convergent_pairs:
        if v1 in merged.columns and v2 in merged.columns:
            valid = merged[[v1, v2]].dropna()
            if len(valid) > 10:
                v1_num = valid[v1].astype(float)
                v2_num = valid[v2].astype(float)
                r, p = stats.pearsonr(v1_num, v2_num)
                met = r > 0 if '正' in expectation else r < 0
                convergent[f'{v1}_vs_{v2}'] = {
                    'r': float(r), 'p': float(p), 'n': len(valid),
                    'expectation': expectation, 'met': bool(met),
                }
                status = '✓' if met else '✗'
                print(f"  {status} {v1} vs {v2}: r={r:.3f}, p={p:.4f}")

    discriminant = {}
    print("\n-- 区分效度 --")
    for v1, v2, expectation in discriminant_pairs:
        if v1 in merged.columns and v2 in merged.columns:
            valid = merged[[v1, v2]].dropna()
            if len(valid) > 10:
                v1_num = valid[v1].astype(float)
                v2_num = valid[v2].astype(float)
                r, p = stats.pearsonr(v1_num, v2_num)
                met = abs(r) < 0.5
                discriminant[f'{v1}_vs_{v2}'] = {
                    'r': float(r), 'p': float(p), 'n': len(valid),
                    'expectation': expectation, 'met': bool(met),
                }
                status = '✓' if met else '✗'
                print(f"  {status} {v1} vs {v2}: r={r:.3f}")

    # 全部新特征间的相关矩阵
    new_feature_cols = ['imperative_verb_count', 'modal_obligation_count', 'modal_prohibition_count',
                        'declarative_predicate_count', 'perfective_aspect_count', 'discourse_temporal_count',
                        'object_argument_count', 't_unit_count', 'clause_density', 'dependency_tree_depth',
                        'noun_entity_count']
    corr_matrix = merged[new_feature_cols].corr()
    corr_matrix.to_csv(os.path.join(RESULT_DIR, '02_validity_correlation_matrix.csv'))

    result = {
        'convergent_validity': convergent,
        'discriminant_validity': discriminant,
        'n_convergent_met': sum(1 for v in convergent.values() if v['met']),
        'n_convergent_total': len(convergent),
        'n_discriminant_met': sum(1 for v in discriminant.values() if v['met']),
        'n_discriminant_total': len(discriminant),
    }
    save_json(result, '02_validity_summary')
    print(f"\n聚合效度: {result['n_convergent_met']}/{result['n_convergent_total']} 符合")
    print(f"区分效度: {result['n_discriminant_met']}/{result['n_discriminant_total']} 符合")

    return merged


if __name__ == '__main__':
    df, feat_df = step1_extract_syntactic_features()
    merged = step2_validity_check(df, feat_df)
    # 保存合并数据
    merged.to_parquet(os.path.join(RESULT_DIR, 'merged_data.parquet'))
    print(f"\n合并数据已保存: {os.path.join(RESULT_DIR, 'merged_data.parquet')}")
