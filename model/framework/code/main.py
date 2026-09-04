# imports
import os
import sys
import numpy as np
from ersilia_pack_utils.core import read_smiles, write_out
from transformers import AutoModel

# parse arguments
input_file = sys.argv[1]
output_file = sys.argv[2]

# current file directory
root = os.path.dirname(os.path.abspath(__file__))

# my model
def my_model(smiles_list):
    model = AutoModel.from_pretrained("Flogrammer/Mol-JEPA", trust_remote_code=True)
    model.eval()
    out = model(smiles_list)
    return out.cls.cpu().numpy()


# read SMILES from .csv file, assuming one column with header
_, smiles_list = read_smiles(input_file)

# run model
outputs = my_model(smiles_list)

#check input and output have the same lenght
input_len = len(smiles_list)
output_len = len(outputs)
print(input_len, output_len)
assert input_len == output_len

num_dims = outputs.shape[1]
header = [f"feat_{str(i).zfill(3)}" for i in range(num_dims)]

# write output in a .csv file
write_out(outputs, header, output_file, np.float32)
