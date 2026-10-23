# imports
import os
import sys
import numpy as np
import torch
from ersilia_pack_utils.core import read_smiles, write_out
from rdkit import Chem
from transformers import AutoModel

# parse arguments
input_file = sys.argv[1]
output_file = sys.argv[2]

# current file directory
root = os.path.dirname(os.path.abspath(__file__))

# Mol-JEPA snapshot (Hugging Face Flogrammer/Mol-JEPA, revision 4c912b4), stored with eosvc
checkpoint_dir = os.path.abspath(os.path.join(root, "..", "..", "checkpoints", "mol-jepa"))

# max atoms (with explicit H) per forward pass. The model builds one graph for all the molecules it
# receives and its memory grows with the atoms in that graph, so this keeps peak memory bounded
# regardless of molecule size. Molecules are never split: one larger than the budget runs alone in
# its own batch. Batching only changes the results by float32 noise, the same as changing the
# batch mates.
ATOMS_PER_BATCH = 2000


def batches(smiles_list):
    batch, n_atoms = [], 0
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        size = Chem.AddHs(mol).GetNumAtoms() if mol is not None else 1
        if batch and n_atoms + size > ATOMS_PER_BATCH:
            yield batch
            batch, n_atoms = [], 0
        batch.append(smi)
        n_atoms += size
    if batch:
        yield batch


# my model
def my_model(smiles_list):
    model = AutoModel.from_pretrained(checkpoint_dir, trust_remote_code=True, local_files_only=True)
    model.eval()
    outputs = []
    with torch.no_grad():
        for batch in batches(smiles_list):
            out = model(batch)
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
