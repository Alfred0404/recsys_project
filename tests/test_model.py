import math

import torch

from src.models.nlgcl import NLGCL


def test_lightgcn_uses_symmetric_degree_normalization_and_layer_mean():
    model = NLGCL(2, 2, dim=1, n_layers=1, contrastive_weight=0)
    edges = torch.tensor([[0, 0, 1], [0, 1, 0]])
    with torch.no_grad():
        model.user_embedding.weight.copy_(torch.tensor([[1.0], [3.0]]))
        model.item_embedding.weight.copy_(torch.tensor([[2.0], [4.0]]))

    users, items = model(edges)
    root2 = math.sqrt(2)
    expected_users = torch.tensor([(1 + 2 / 2 + 4 / root2) / 2, (3 + 2 / root2) / 2])
    expected_items = torch.tensor([(2 + 1 / 2 + 3 / root2) / 2, (4 + 1 / root2) / 2])
    torch.testing.assert_close(users[:, 0], expected_users)
    torch.testing.assert_close(items[:, 0], expected_items)


def test_contrastive_objective_changes_loss_without_changing_graph_or_bpr():
    model = NLGCL(3, 3, dim=4, contrastive_weight=0.05)
    graph = torch.tensor([[0, 0, 1, 2], [0, 1, 1, 2]])
    users, pos = graph
    neg = torch.tensor([2, 2, 0, 0])
    total, bpr, contrastive = model.loss_parts(users, pos, neg, graph)
    assert contrastive.item() > 0
    total.backward()
    assert torch.isfinite(model.user_embedding.weight.grad).all()
    assert torch.isfinite(model.item_embedding.weight.grad).all()

    ablation = NLGCL(3, 3, dim=4, contrastive_weight=0)
    ablation.load_state_dict(model.state_dict())
    ablated_total, ablated_bpr, ablated_contrastive = ablation.loss_parts(users, pos, neg, graph)
    torch.testing.assert_close(bpr, ablated_bpr)
    torch.testing.assert_close(total - ablated_total, 0.05 * contrastive)
    assert ablated_contrastive.item() == 0
