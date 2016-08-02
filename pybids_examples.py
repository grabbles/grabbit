
# get func, t1w, and fmap for two particular subjects
# only take run 2 for motor task
# HOW TO DEAL WITH RUN SINCE IT COULD REFER TO FUNC OR T1W?
# ANOTHER TRICK WITH FIELDMAPS - DO WE RETURN ONLY THE FIELDMAPS
# THAT MATCH THE SPECIFIC FUNCTIONAL RUN BEING RETURNED?

pybids_instance = pybids(path='/home/chris/bids_data', config='this_config.json')
filtered_output=pybids_instance.searcher(sub=['01','02'],
        image_type=['T1w','bold','fmap'],relative_path=True,
        ext='nii',return_as_list=False,flatten=False,
        filter={'run':['02'],'task':['motor']}})

{'basedir':'<base directory for dataset>',
'01':{
    '01':{
        'T1w':['anat/sub-01_run-01_T1w.nii.gz','anat/sub-01_run-02_T1w.nii.gz'],
        'func':['func/sub-01_run-02_task-motor_bold.nii.gz'],
        'fmap':['fmap/sub-01_magnitude.nii.gz']},
        },
'02':{
    '01':{
        'T1w':['anat/sub-02_run-01_T1w.nii.gz'],
        'func':['func/sub-02_run-01_task-motor_bold.nii.gz'],
        'fmap':['fmap/sub-02_magnitude.nii.gz']}
        }
}


### OLDER


pybidgetter=PyBIDS.getter(pipeline=None)

# get all T1w and T2w images from a dataset
# say there are three subjects - subj 3 is missing its T1w

output=pybidgetter(image_type=['T1w'])

{'basedir':'<base directory for dataset>',
'sub-01':{
    'T1w':['anat/sub-01_run-01_T1w.nii.gz','anat/sub-01_run-02_T1w.nii.gz'],
    'T2w':['anat/sub-01_run-01_T2w.nii.gz','anat/sub-01_run-02_T2w.nii.gz']},
'sub-02':{
    'T1w':['anat/sub-02_run-01_T1w.nii.gz','anat/sub-02_run-02_T1w.nii.gz'],
    'T2w':['anat/sub-02_run-01_T2w.nii.gz','anat/sub-02_run-02_T2w.nii.gz']},
'sub-03':{
    'T2w':['anat/sub-03_run-01_T2w.nii.gz','anat/sub-03_run-02_T2w.nii.gz']}
}
