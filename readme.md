# CV Master Label Assignment

作业划分为不同的难度档次，对应不同的星级(满分为5星)，可根据自己的时间和能力自主选择任务(基础任务星级不可叠加，按完成的最高星级计算成绩；附加任务星级可叠加：

基础任务
【2 ⭐】: 实现Freeanchor/FCOS任意一种

【3 ⭐】: 实现ATSS

【4 ⭐】: 实现Auto-assign/PAA(简化版)任意一种

附加任务
【0.5 ⭐】：优化基础任务中的label assginment，给出前后测试集指标对比(可截图)和优化思路、自己的理解

【0.5 ⭐】：实现至少两种不同星级的基础任务并比较他们的label assignment(可利用统计、可视化等手段)，给出自己的理解

## Retinanet的LabelAssignment设计

为经典Achor based Label Assignment
使用Anchor box进行bbox定位，Anchor box位置表示使用(x_ctr,y_ctr,w,h)，要做offset的是(x_ctr,y_ctr,w,h)
采用Base Anchor box同gt_box进行比对，通过两者IOU给Anchor box赋不同标签（postive、negative和ignore）

## FCOS LabelAssignment设计要点

### Anchor-free 方式

box_head相比retinanet结构不同，box_head layer需要重写

（1）多了一个centerness输出

（2）bbox回归输出也变成Anchor point距离bbox边框距离 （l,r,b,t）

### Label Assignment

LabelAssignment方式不同，AnchorGenerator以及get_ground_truth函数需要重写

（1）由于FCOS采用Location Point方法，无须给出anchor的形状，故无需生成base anchor的函数，一个grid仅需要num_anchors个Location Points

（2）采用FPN作为backbone，get_ground_truth主要实现解决层内歧义的center sampling和解决层间歧义的scale划分

对应参数为center_sampling_radius和object_size_of_interest

主要步骤为：

1）将object_size_of_interest拓展到每一层特征对应的anchor points

2）将所有feature map上anchor point映射回原图，计算其与所有gt box框的距离

3）依据scale规则，得出positive

4）计算gt_box的center sampling区域，依据在center区域内得出positive

5）将negtive的area设定为inf

6）计算所有positive anchor points对应最小area的gt_box

### Loss的改变

回归Loss采用IOU Loss，输入为Anchor point距离bbox四边框距离(l,r,b,t)，要做offset的也是(l,r,b,t)

## ATSSLabelAssignment 设计要点

ATSS提出了利用自适应阈值进行Bbox Assignment，可基于Anchor-free方式实现

故需要实现的是ATSS提出的Assignment规则，也即get_ground_truth函数，ATSS提出的规则按步骤：

1）计算每个 gt bbox 和多尺度输出层的所有 anchor 之间的 IoU

2）计算每个 gt bbox 中心坐标和多尺度输出层的所有 anchor 中心坐标的 l2 距离

3）遍历每个输出层，遍历每个 gt bbox，找出当前层中 topk (超参，默认是 9 )个最小 l2 距离的 anchor 。假设一共有 L 个输出层，那么对于任何一个 gt bbox，都会挑选出 topk*L 个侯选位置

4）对于每个 gt bbox，计算所有候选位置 IoU 的均值和标准差，两者相加得到该 gt bbox 的自适应阈值

5）遍历每个 gt bbox，选择出候选位置中 IoU 大于阈值的位置，该位置认为是正样本，负责预测该 gt bbox
