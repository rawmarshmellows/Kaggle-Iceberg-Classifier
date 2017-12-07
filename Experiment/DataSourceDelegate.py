import pandas as pd
import torch
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from src.utils import create_dataloader
from .AbstractDataSourceDelegate import AbstractDataSourceDelegate


class DataSourceDelegate(AbstractDataSourceDelegate):
    def __init__(self, training_data_path, batch_size):
        self.training_data_path = training_data_path
        self.batch_size = batch_size
        self.splits = None
        self.data = None
        self.setup()

    def _get_data_reader(self, path):
        file_extension = path.split(".")[-1]
        return {
            "csv": pd.read_csv,
            "json": pd.read_json
        }.get(file_extension)

    def setup(self):
        data = self.load_data()
        preprocessed_data = self.preprocess_data(data)
        self.splits = self.data_split(preprocessed_data)
        self.data = preprocessed_data

    def load_data(self):
        path = self.training_data_path
        assert path is not None
        data_reader = self._get_data_reader(path)
        return data_reader(path)

    def preprocess_data(self, data):

        logging.info("Preprocessing data ...")
        logging.info("Reshaping input images ...")
        data['band_1_rs'] = data['band_1'].apply(lambda x: np.array(x).reshape(75, 75))
        data['band_2_rs'] = data['band_2'].apply(lambda x: np.array(x).reshape(75, 75))
        data['band_3_rs'] = (data['band_1_rs'] + data['band_2_rs']) / 2
        data['inc_angle'] = pd.to_numeric(data['inc_angle'], errors='coerce')

        band_1 = np.concatenate([im for im in data['band_1_rs']]).reshape(-1, 75, 75)
        band_2 = np.concatenate([im for im in data['band_2_rs']]).reshape(-1, 75, 75)
        band_3 = np.concatenate([im for im in data['band_3_rs']]).reshape(-1, 75, 75)

        logging.info("Converting training data to Tensors ...")

        # Batch, Height, Width, Channel
        img = np.stack([band_1, band_2, band_3], axis=3)
        img_max = np.max(img, keepdims=True, axis=(1, 2))
        img_min = np.min(img, keepdims=True, axis=(1, 2))
        max_min_diff = img_max - img_min
        imgs_uint8 = (((img - img_min) / max_min_diff) * 255).astype(np.uint8)

        if 'is_iceberg' in data:
            targets = data['is_iceberg'].values
        else:
            targets = [-1] * data.shape[0]

        img_ids = data['id'].tolist()
        df_dict = []
        for img, target, img_id in zip(imgs_uint8, targets, img_ids):
            df_dict.append({
                "input": img,
                "label": target,
                "id": img_id
            })

        df = pd.DataFrame(df_dict)
        return df

    def data_split(self, data):
        folds = KFold(n_splits=5).split(data)
        return folds

    def retrieve_dataset(self):
        for train_idx, test_idx in self.splits:
            train_df = self.data.iloc[train_idx]
            val_df = self.data.iloc[test_idx]
            train_dataloader = create_dataloader(train_df, is_train=True,
                                                 batch_size=self.batch_size)
            val_dataloader = create_dataloader(val_df, is_train=False,
                                               shuffle=False,
                                               batch_size=self.batch_size)
            yield {"train": train_dataloader,
                   "val": val_dataloader}












