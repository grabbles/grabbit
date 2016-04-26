# use cases and API

## template file may look like:


    >>> templates={"T1": "{subject_id}/struct/T1.nii",
    ...            "epi": "{subject_id}/func/f[0, 1].nii"}
    >>> dg = Node(SelectFiles(templates), "selectfiles")
	
	entities:[subject:sub, session:ses, run:run, smoothed, mvt6param]
	base_dir:''

	# if there is a pattern for the values, this would not be needed:
	#----------------------------------------------------------------
	'subject':{'key':'sub', 'lnk':'-', 'val':'02d'}
	# and we can have directly:
	'smoothed?dir:{base_dir}/sub-{sub:02d}/ses-{ses-:02d}/preproc/{run-:02d}/
	'smoothed?file:sub-{sub:02d}_ses-{ses-:02d}_{run-:02d}_epi.[nii,nii.gz]

	# If subjects values are not rule-based, this would be needed:
	#----------------------------------------------------------------
	'subject':{'key':'sub', 'lnk':'-', 'val':['1','2','3','toto']}
	'session':{'key':'ses', 'lnk':'-', 'val':['1','2','3','too_many']}
	'run':{'key':'run', 'lnk':'-', 'val':['1','2','3','5','17','0']}
	# in which case we can have:
	smoothed?pth:{base_dir}/{subject}/{session}/preproc/{run}/
	smoothed?files:{subject}_{session}_{run}_epi.[nii,nii.gz]

	# Possibly a mixe:
	smoothed_dr:{base_dir}/sub-{sub:02d}/ses-{ses-:02d}/preproc/{run-:02d}/
	smoothed_fn:sub-{sub:02d}_ses-{ses-:02d}_{run-:02d}_epi.[nii,nii.gz]

	# if either nii or nii.gz but not both:
	smoothed_fn:sub-{sub:02d}_ses-{ses-:02d}_{run-:02d}_epi.[nii|nii.gz]

	

## instanciate a template ds 
	
	# 
	ds = data_structure("a_json_file.json")

	# list elements in this template:
	entities = ds.list()

	# other ?

# retrieve : 

	# for example, get a list of subjects, 



