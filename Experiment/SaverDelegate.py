from .AbstractSaverDelegate import AbstractSaverDelegate
import numpy as np
import logging
import os
import torch
from pathlib import Path


class SaverDelegate(AbstractSaverDelegate):

    def __init__(self, experiment_id, study_save_path, generation=0):
        super().__init__()
        self.experiment_id = experiment_id
        self.study_save_path = study_save_path
        self.generation = generation
        self.last_epoch_validation_loss = None # TODO: use property method

    def on_model_loss(self, loss, mode):
        if mode == "TRAIN":
            self.training_loss_for_epoch.append(loss.data)
        else:
            self.validation_loss_for_epoch.append(loss.data)

    def _save_model(self, model, epoch, fold_num, loss):
        models_checkpoint_folder_path = Path(
            f"{self.study_save_path}/generation_{self.generation}/{self.experiment_id}/model_checkpoints/fold_{fold_num}")
        models_checkpoint_folder_path.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), os.fspath(f"{models_checkpoint_folder_path}/epoch_{epoch}-loss_{loss}.pth"))

    def on_epoch_end(self, model, epoch, fold_num):
        avg_loss, = np.mean(np.array(self.training_loss_for_epoch)).cpu().numpy()
        self.training_results[fold_num].update({epoch: avg_loss})
        logging.info(f"Training loss for epoch: {epoch} is {avg_loss}")

        avg_val_loss, = np.mean(np.array(self.validation_loss_for_epoch)).cpu().numpy()
        self.last_epoch_validation_loss = avg_val_loss
        self.validation_results[fold_num].update({epoch: avg_val_loss})
        logging.info(f"Validation loss for epoch: {epoch} is {avg_val_loss}")
        self._save_model(model, epoch, fold_num, avg_val_loss)

        self.training_loss_for_epoch = []
        self.validation_loss_for_epoch = []

