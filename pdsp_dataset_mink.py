from torch.utils.data import Dataset, DataLoader

import MinkowskiEngine as ME

import torch
import torch.nn as nn

import process_hits
from dataclasses import dataclass

@dataclass
class Config:
  batch_size: int
  num_workers: int = 1


##Only uses plane 2
class PDSPDataset(Dataset):
  def __init__(self, pdsp_data):
    super().__init__()
    self.pdsp_data = pdsp_data

  def __len__(self):
    return self.pdsp_data.nevents

  def __getitem__(self, i: int) -> dict:
    locs, features = self.pdsp_data.get_plane(i, 2)
    label = self.pdsp_data.topos[i]

    return {
      'coordinates': torch.from_numpy(locs).to(torch.long),
      'features': torch.from_numpy(features).to(torch.float32),
      'label': torch.LongTensor([label])
    }

def minkowski_collate_fn(list_data):
    coordinates_batch, features_batch, labels_batch = ME.utils.sparse_collate(
        [d["coordinates"] for d in list_data],
        [d["features"] for d in list_data],
        [d["label"] for d in list_data],
        dtype=torch.float32,
    )
    return {
        "coordinates": coordinates_batch,
        "features": features_batch,
        "labels": labels_batch,
    }

def get_dataset(pdsp_data):
  dataset = PDSPDataset(pdsp_data)
  return dataset

def get_loader(pdsp_data, config):
  dataset = PDSPDataset(pdsp_data)

  return DataLoader(
    dataset,
    num_workers=1, ##config.num_workers
    collate_fn=minkowski_collate_fn,
    batch_size=config.batch_size,
  )


class PDSPDatasetAllPlanes(Dataset):
  def __init__(self, pdsp_data):
    super().__init__()
    self.pdsp_data = pdsp_data

  def __len__(self):
    return self.pdsp_data.nevents

  def __getitem__(self, i: int) -> dict:

    label = self.pdsp_data.topos[i]
    data = {
     'label' :torch.LongTensor([label])
    }

    for j in range(3):
      locs, features = self.pdsp_data.get_plane(i, j)
      data[f'coordinates_{j}'] = torch.from_numpy(locs).to(torch.long)
      data[f'features_{j}'] = torch.from_numpy(features).to(torch.float32)
    return data

def get_dataset_allplanes(pdsp_data):
  return PDSPDatasetAllPlanes(pdsp_data)
def minkowski_collate_fn_all_planes(list_data):

    coordinates_0 = []
    coordinates_1 = []
    coordinates_2 = []

    features_0 = []
    features_1 = []
    features_2 = []

    labels = []
    for d in list_data:
      coordinates_0.append(d['coordinates_0'])
      coordinates_1.append(d['coordinates_1'])
      coordinates_2.append(d['coordinates_2'])

      features_0.append(d['features_0'])
      features_1.append(d['features_1'])
      features_2.append(d['features_2'])

      labels.append(d['label'])

    coordinates_0, features_0, labels = ME.utils.sparse_collate(
        coordinates_0,
        features_0,
        labels,
        dtype=torch.float32,
    )

    coordinates_1, features_1 = ME.utils.sparse_collate(
        coordinates_1,
        features_1,
        dtype=torch.float32,
    )

    coordinates_2, features_2 = ME.utils.sparse_collate(
        coordinates_2,
        features_2,
        dtype=torch.float32,
    )

    return {
        "coordinates_0": coordinates_0,
        "features_0": features_0,
        "coordinates_1": coordinates_1,
        "features_1": features_1,
        "coordinates_2": coordinates_2,
        "features_2": features_2,
        "labels": labels,
    }
