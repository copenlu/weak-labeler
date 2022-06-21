import torch
from torch import nn
import torch.nn.functional as F
from typing import Dict

import argparse
import pandas as pd
from model import Transformer_classifier
import sys
from transformers import AutoTokenizer
from weaklabeler.fewShot.data import FewShotData

from tqdm import tqdm
tqdm.pandas()

from weaklabeler.tools.transformer_tok import transformer_tok
from weaklabeler.tools.utils import get_targets, get_available_cpus
from torch.utils.data import DataLoader

from typing import List


def batcher(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def predict(texts:List , model:nn.Module, target_dict: Dict = {}, tokenizer: AutoTokenizer = None) -> str:
    """

    Custom Inference

    Args:
        texts (List): text for prediction
        model (nn.Module): model for inference
        taget_dict (_type_, optional):  Mapping between Ids to class. Defaults to {}.

    Returns:
        str: predicted class
    """

    predictions = []

    train_dataset = FewShotData(data = texts, labels = None, tokenizer = tokenizer, target_dict=target_dict )
    print(target_dict)

    available_workers = get_available_cpus()
    train_dataloader = DataLoader(train_dataset, batch_size = 64, shuffle=False, num_workers = available_workers)

    with torch.inference_mode():

        for batch in tqdm(train_dataloader):

            batch_input = {k: v.to('cuda') for k, v in batch.items()}
            # batch_labels = batch_input['labels'].view(-1)

            # logits = model(**batch_input)

            logits = model(**batch_input)
            probs = F.softmax(logits, dim=1)

            for index in range(len(probs)):
                prob = probs[index]
                # print(target_dict[str(torch.argmax(prob).item())])
                predictions.append(target_dict[str(torch.argmax(prob).item())])

        # inputs = [transformer_tok(text, tokenizer) for text in text_batch]
        # inputs = [{'input_ids': inp['input_ids'].cuda(),'attention_mask':inp['attention_mask'].cuda() } \
        #             for inp in inputs]

        # for input in tqdm(inputs):
        #     input['labels'] = 1
        #     with torch.inference_mode():
        #         logits = model(**input)
        #         probs = F.softmax(logits, dim=1).squeeze(dim=0)

        #         predictions.append(target_dict[torch.argmax(probs).item()])

    return predictions


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
    description="Transformer Inference"
    )

    parser.add_argument(
    '--model_path',
    help="The path of the model to load"
    )

    parser.add_argument(
    '--feat_extractor',
    help="The name of the feature extractor transformer"
    )

    parser.add_argument(
    '--text_col',
    help="Name of column containing training text"
    )

    parser.add_argument(
    '--test_path',
    help="The path of the test"
    )

    parser.add_argument(
    '--target_config_path',
    help="Path to target config file, with the mapping from target to id"
    )

    args = parser.parse_args()


    model = torch.load(args.model_path,'cpu')
    model.to("cuda")

    tokenizer = AutoTokenizer.from_pretrained(args.feat_extractor, use_fast=True)
    test = pd.read_csv(args.test_path, index_col=0)
    target_dict = get_targets(args.target_config_path)


    print("Predicting...\n")
    test['topic_pred'] = predict(test[args.text_col], model=model,target_dict=target_dict,tokenizer=tokenizer)

    test.to_csv('results.csv')