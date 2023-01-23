import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import kss
import torch
from transformers import PreTrainedTokenizerFast
from transformers import GPT2LMHeadModel



def main_inference(model_path, max_len, data):

    OUTPUT_TKN = "<usr>"
    RESULT_TKN = "<sys>"
    BOS = '</s>'
    EOS = '</s>'
    MASK = '<unused0>'
    SENT = '<unused1>'
    PAD = '<pad>'

    start_time = time.time()
    tokenizer = PreTrainedTokenizerFast.from_pretrained(model_path,
                bos_token=BOS, eos_token=EOS, unk_token='<unk>',
                pad_token=PAD, mask_token=MASK) 
    model = GPT2LMHeadModel.from_pretrained(model_path)

    sent = '0'
    sentences = []
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    answer=""

    with torch.no_grad():
        for sentence in kss.split_sentences(data) :
            query = sentence
            print(f'query : {query}')
            answer = ""
            
            if query is not np.nan:
                while True:
                    input_ids = torch.LongTensor(tokenizer.encode(OUTPUT_TKN + query + SENT + sent + RESULT_TKN + answer)).unsqueeze(dim=0)
                    input_ids = input_ids.to(device)
                    pred = model(input_ids)
                    pred = pred.logits
                    if pred.shape[1]>max_len:
                        print("error!!")
                        break
                    gen = tokenizer.convert_ids_to_tokens(torch.argmax(pred, dim=-1).squeeze().cpu().numpy().tolist())[-1]
                    if gen == EOS:
                        break
                    answer += gen.replace("▁", " ")
                print(f"answer : {answer.strip()}")
                sentences.append(answer.strip())
            else:
                sentences.append(query)
                
    print(f'sec : {time.time()-start_time}')
    return sentences


if __name__ == '__main__':
    result = main_inference(model_path = '/opt/ml/espnet-asr/final/GPT_2/', max_len = 64,
                       df = '/opt/ml/espnet-asr/[심화별개념5]_2_1구석기_신석기시대_2강선사시대_dataset.csv/')
    