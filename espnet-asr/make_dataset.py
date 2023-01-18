
from collections import defaultdict
from itertools import combinations
from typing import Optional
import re
import os
import pandas as pd

def delete_loop(text):
    new_text = text[:]
    tmp = text.split()
    arr = [i for i in range(len(tmp)+1)]
    can_list = [com for com in combinations(arr, 2) if com[1] - com[0] + 1 <= len(arr)-com[1]]
    for can in can_list:
        string = tmp[can[0]:can[1]]
        stick = can[1]
        len_string = len(string)
        cnt = 0
        for i in range((len(arr) - can[1]) // (can[1] - can[0])):
            end_stick = stick + len_string
            if string != tmp[stick:end_stick]:
                continue
            cnt += 1
            stick = end_stick
        if cnt != 0:
            new_tmp = tmp[:can[1]] + tmp[can[1] + len_string*cnt:]
            new_text = ' '.join(new_tmp)
            break
    if text == new_text:
        return text
    else:
        return delete_loop(new_text)

def make_new_dataset(output_file_paths: str, labeled_file_paths: Optional[str]):
    # 1. create dictionary and add labeled data
    output = defaultdict(list)
    if labeled_file_paths:
        idx = labeled_file_paths[0].split('/')[-5]      # KlecSpeech_train_D12_label_0
        folder = labeled_file_paths[0].split('/')[-2]   # S001007
        for labeled_file_path in labeled_file_paths:
            print(labeled_file_path)
            i = labeled_file_path.split('/')[-1].split('.')[0]
            extension = labeled_file_path.split('/')[-1].split('.')[1]

            domain = labeled_file_path.split('/')[-4]
            subdomain = labeled_file_path.split('/')[-3]

            # json 파일 제외
            if extension == 'txt':
                with open(labeled_file_path, 'r+') as f:
                    line = f.readline().strip()

                # preprocessing
                # step  (그러니까)/(긍게*) 짧으니까 쓰기가 쉽죠.
                for match in set(re.findall(r'\([^)]*\)[\s]*[/][\s]*\([^)]*\)', line)):
                    repl = match.split('/')[0][1:-1]
                    line = line.replace(match, repl)
                
                # step 이 작품이 쓰여진 건 (60)/)육십) 년대 와서야 이루어졌습니다. 왜냐하면 전쟁 때는,
                for match in set(re.findall(r'\([^)]*\).*\)', line)):
                    repl = re.findall(r'\([^)]*\)', match)[0][1:-1]
                    line = line.replace(match, repl)
                
                # step  (그러니까)(긍게*) 짧으니까 쓰기가 쉽죠.
                for match in set(re.findall(r'\([^)]*\)[^)]*\)', line)):
                    repl = re.findall(r'\([a-zA-Z가-힣]+\)', line)[0][1:-1]
                    line = line.replace(match, repl)
                
                # step . change '[kr]/' -> [kr] 
                for match in set(re.findall(r'[가-힣][/]', line)):
                    repl = match[:-1]
                    line = line.replace(match, repl)

                # step . change '[en]/' -> ''
                for match in set(re.findall(r'[a-zA-Z][/]', line)):
                    repl = ''
                    line = line.replace(match, repl)

                # step . change '[kr, en]+' -> ''
                for match in set(re.findall(r'[a-zA-Z가-힣]{1}[+]\s', line)):
                    repl = ''
                    line = line.replace(match, repl)

                # step . change '[kr, en]*' -> ''
                repl = ''
                line = line.replace('*', repl)

                # step 4. @/ -> ''
                line = re.sub(r'[@][/]', '', line)
                
                # step 4. /, ／ -> ''
                line = line.replace('/', '')
                line = line.replace('／', '')
                
                # step 7. '  ' -> ' '
                repl = ''
                line = line.replace('  ', ' ')

                # step 8. '+' -> ' '
                repl = ' '
                line = line.replace('+', ' ')
                line = line.replace('＋', ' ')

                # step
                line = line.replace('ｌ', '')

                # key : KlecSpeech_train_D12_label_0-D12-G02-S001007-000625
                key = idx + '-' + domain + '-' + subdomain + '-' + folder + '-' + i
                output[key].append(line.strip())

    # 2. add output data in dictionary
    for output_file_path in output_file_paths:
        try:
            _, domain, subdomain = output_file_path.split('/')[3:6]
        except ValueError as e:
            pass

        with open(output_file_path, 'r+') as f:
            lines = f.readlines()
        for line in lines:
            line_split = line.split(' ') 
            i, line = line_split[0], " ".join(line_split[1:])
            
            # TODO : output 후처리
            line = delete_loop(line)

            try:
                key = idx + '-' + domain + '-' + subdomain + '-' + folder + '-' + i
            except UnboundLocalError as e:
                key = i
            output[key].append(line.strip())
    
    # 3. add null values
    for key, value in output.items():
        if len(value) < 2:
            output[key].append('')
            output[key] = output[key][::-1]
    df = pd.DataFrame(output).T
    df.rename(columns={0: 'label', 1: 'output'}, inplace=True)
    return df

# make inference dataset
def inference_dataset(filename) -> pd.DataFrame:
    output_path = os.path.join('output', filename)

    dfs = pd.DataFrame({'label': [], 'output': []})
    
    output_file_paths = []
    for e in os.listdir(output_path):
        output_folder_path = os.path.join(output_path, e, '1best_recog')
        output_file_path = os.path.join(output_folder_path, 'text')
        output_file_paths.append(output_file_path)

    df = make_new_dataset(output_file_paths, None)
    dfs = pd.concat([dfs, df])
    
    dfs.index = [int(idx.split('-')[-1]) for idx in dfs.index]
    dfs = dfs.sort_index()
    dfs.to_csv(f'./{filename}_dataset.csv', encoding='utf-8-sig')

    return dfs


# make train or validataion dataset -> stage: train, validataion
def aihub_dataset(stage='train'):
    label_path = os.path.join('dataset', stage, 'labeled_data')
    output_path = os.path.join('output', stage, 'raw_data')

    dfs = pd.DataFrame({'label': [], 'output': []})
    for idx in sorted(os.listdir(output_path)):
        for domain in sorted(os.listdir(os.path.join(output_path, idx))):
            for subdomain in sorted(os.listdir(os.path.join(output_path, idx, domain))):
                for directory in sorted(os.listdir(os.path.join(output_path, idx, domain, subdomain))):

                    output_folder_path = os.path.join(output_path, idx, domain, subdomain, directory)
                    output_file_paths = sorted([
                        os.path.join(output_folder_path, file, '1best_recog', 'text')
                        for file in os.listdir(output_folder_path)
                    ])

                    labeled_idx = idx.split('_')
                    labeled_idx[-2] = 'label'
                    labeled_idx = "_".join(labeled_idx)
                    labeled_folder_path = os.path.join(label_path, labeled_idx ,domain, subdomain, directory)
                    labeled_file_paths = sorted([
                        os.path.join(labeled_folder_path, file)
                        for file in os.listdir(labeled_folder_path)
                    ])
                    df = make_new_dataset(output_file_paths, labeled_file_paths)
                    dfs = pd.concat([dfs, df])
    dfs.to_csv(f'./{stage}_dataset.csv', encoding='utf-8-sig')