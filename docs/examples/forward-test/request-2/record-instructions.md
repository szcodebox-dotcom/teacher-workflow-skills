# 复测记录使用

retest-point-records.csv是待填写记录格式，预置题号、评分项和满分，未实施的得分留空、状态为unscored。空白是未评分字段，不是已交付题面的占位内容。S01–S04为本次合成标识。

按每个可观察项录入earned_score（此文件各项满分1），保留原作答，observed_evidence写实际可观察操作，hint_used记录是否有提示，minutes写实际用时。point_id对应new-exercises-answers-and-scoring.md逐点顺序。得分与记录状态一致：记录的0分是已评分且无相应证据，空分是未取得评分。

导出给学情脚本时按exam_id/student_id/question_id合计earned_score、max_score；只要本题任何评分项未评分，该题score应为空，不以0补齐；知识点为解方程/建模。列仍为exam_id,student_id,question_id,knowledge_point,score,max_score。每题评分点均有记录才算题目已评分，每卷两题均有评分才算整卷完整。提示练习与无提示测验必须使用不同exam_id。
