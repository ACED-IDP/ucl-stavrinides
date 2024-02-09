# Processing notes regarding the clinical data#

Y. Lu 2024-0206

Preprocessing:
* Replaced spaces in variable names with underscore, i.e. 'Gleason_3_Area'

Notes:
* The following features are experimental features extracted from imaging by a DL classifier/regressor: Epi_Count, Stroma_Count, Lymphocyte_Count, Lymphocyte_Percentage, Irani_Gscore, Tissue_Area, Epithelial_Area, Stromal_Area, Inflammatory_Area, Epithelial_Area_Percentage, Stromal_Area_Percentage, Inflammatory_Area_Percentage, Epithelial_Stromal_Ratio, Lumen_Area, Lumen_Density, Lumen_Density_Gland, Annotated_Cancer_Area, Normal_Area, PIN_Area, Gleason_3_Area, Gleason_4_Area, Gleason_5_Area, Gleason_Primary, Gleason_Secondary, Grade_Group
* when the feature 'zone' is SV, the record will be excluded - the dummy dataset does not have the SV flag in the zone feature.
* (ageDiagM, ageDiagY) are fixed for each pid - ageDiagM = ageDiagY*12 + random.randint(0, 11)
* the 'precise' feature should only be filled for time point B
* Note, the cluster code in the pid, can be 'A1', 'A2'. It's not just limited to one alphabet letter.
    * [TBC] ask VS to clean up this feature

* filled values are filled with the following functions
    * int: random.randint
    * float: random.uniform
    * string: random.choice