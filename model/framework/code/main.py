# imports
import os
import sys
import numpy as np
import torch
from ersilia_pack_utils.core import read_smiles, write_out
from transformers import AutoModel

# parse arguments
input_file = sys.argv[1]
output_file = sys.argv[2]

# current file directory
root = os.path.dirname(os.path.abspath(__file__))

# Mol-JEPA snapshot (Hugging Face Flogrammer/Mol-JEPA, revision 4c912b4), stored with eosvc
checkpoint_dir = os.path.abspath(os.path.join(root, "..", "..", "checkpoints", "mol-jepa"))

# molecules per forward pass. The model builds one graph for all the molecules it receives and
# its memory grows linearly with them (~15 MB per molecule on CPU), so a 10,000-molecule input in
# one call needs > 128 GB. With 400 a 10,000-molecule input peaks at ~7 GB. Chunking only changes
# the results by float32 noise (max abs diff ~4e-7), the same as changing the batch mates.
CHUNK_SIZE = 400

# my model
def my_model(smiles_list):
    model = AutoModel.from_pretrained(checkpoint_dir, trust_remote_code=True, local_files_only=True)
    model.eval()
    outputs = []
    with torch.no_grad():
        for i in range(0, len(smiles_list), CHUNK_SIZE):
            out = model(smiles_list[i:i + CHUNK_SIZE])
            outputs.append(out.cls.cpu().numpy())
    return np.concatenate(outputs, axis=0)


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
