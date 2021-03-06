import torch
import torch.nn as nn
import torch.nn.functional as F

class HardDice(nn.Module):
    def __init__(self,
                 threshold=0.5,
                 deduct_intersection=False):
        super().__init__()
        self.threshold = threshold
        self.deduct_intersection = deduct_intersection
        
    def forward(self, outputs, targets):
        eps = 1e-10
        
        dice_target = (targets == 1).float()
        dice_output = F.sigmoid(outputs)    
        hard_output = (dice_output > self.threshold).float()
        
        intersection = (hard_output * dice_target).sum()
        if self.deduct_intersection:
            union = hard_output.sum() + dice_target.sum() - intersection + eps
        else:
            union = hard_output.sum() + dice_target.sum() + eps
        
        hard_dice = (1+torch.log(2 * intersection / union))
        hard_dice = torch.clamp(hard_dice,0,1)
        return hard_dice

# Focal loss implementation inspired by
# https://github.com/c0nn3r/RetinaNet/blob/master/focal_loss.py
# https://github.com/doiken23/pytorch_toolbox/blob/master/focalloss2d.py
class MultiClassBCELoss(nn.Module):
    def __init__(self,
                 use_weight_mask=False,
                 use_focal_weights=False,
                 focus_param=2,
                 balance_param=0.25
                 ):
        super().__init__()

        self.use_weight_mask = use_weight_mask
        self.nll_loss = nn.BCEWithLogitsLoss()
        self.use_focal_weights = use_focal_weights
        self.focus_param = focus_param
        self.balance_param = balance_param
        
    def forward(self,
                outputs,
                targets,
                weights=None):
        # inputs and targets are assumed to be BatchxClasses
        assert len(outputs.shape) == len(targets.shape)
        assert outputs.size(0) == targets.size(0)
        assert outputs.size(1) == targets.size(1)
        
        if weights is not None:
            # weights are assumed to be BatchxClasses
            assert outputs.size(0) == weights.size(0)
            assert outputs.size(1) == weights.size(1)

        if self.use_weight_mask:
            bce_loss = F.binary_cross_entropy_with_logits(input=outputs,
                                                          target=targets,
                                                          weight=weights)            
        else:
            bce_loss = self.nll_loss(input=outputs,
                                     target=targets)
        
        if self.use_focal_weights:
            logpt = - bce_loss
            pt    = torch.exp(logpt)

            focal_loss = -((1 - pt) ** self.focus_param) * logpt
            balanced_focal_loss = self.balance_param * focal_loss
            
            return balanced_focal_loss
        else:
            return bce_loss 