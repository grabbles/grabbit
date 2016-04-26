# use cases and API

## template file may look like:
	
	{
	    'base_dir':'',
	    'entities':{
		'names':['subject', 'session', 'run', 'smoothed', 'mvt6param'],
		'subject':{'key':'sub', 'lnk':'-', 'val':'02d'},
		'session':{'key':'ses', 'lnk':'-', 'val':'02d'},
		'run':{'key':'run', 'lnk':'-', 'val':'02d'}
	    }

	    # If subjects values are not rule-based, this would be needed:
	    #----------------------------------------------------------------
	    'subject':{'key':'sub', 'lnk':'-', 'val':['1','2','3','toto']}
	    'session':{'key':'ses', 'lnk':'-', 'val':['1','2','3','too_many']}
	    'run':{'key':'run', 'lnk':'-', 'val':['1','2','3','5','17','0']}

	    # and we can have directly:
	    'smoothed':{
		'pth':'{base_dir}/sub-{sub:02d}/func/ses-{ses-:02d}/preproc/{run-:02d}/',
		'file':'sub-{sub:02d}_ses-{ses-:02d}_{run-:02d}_epi.[nii,nii.gz]'
	    }

	    # in which case we can have:
	    'smoothed':{
		'pth':'{base_dir}/{subject}/{session}/preproc/{run}/',
		'file':'{subject}_{session}_{run}_epi.[nii,nii.gz]'
	    }

	    # Possibly a mix: we can have:
	    'smoothed':{
		'pth':'{base_dir}/sub-{sub:02d}/{session}/preproc/{run}/',
		'fln':'{subject}_{session}_{run}_epi.[nii,nii.gz]', '#':'==1',
		# other for '#': '>=1', '==1', '>=0', '[3,5[', 
		# default: '>=0'
		# if either nii or nii.gz but not both:
		'fln':'{subject}_{session}_{run}_epi.[nii|nii.gz]'
	    }

	    # could also be:
	    'smoothed':'{base_dir}/{subject}/{session}/preproc/{run}/\
			{subject}_{session}_{run}_epi.[nii,nii.gz]'
	}
	

## instanciate a template ds 
	
	# 
	ds = data_structure("a_json_file.json", base_dir='/some/optional/path/')

# retrieve information: 

	# list elements in this template:
	entities = ds.list()
	# get the smoothed entity filenames:
	smoothed_filenames = ds.smoothed.filenames()

	# get specific smoothed entities filenames:
	current_dict = {'sub':3, 'ses':2, 'run':1}
	one_smoothed_file_name = ds.smoothed.filenames(statedict=current_dict, card='==1')
	current_dict = {'sub':3, 'ses':[1,2,3], 'run':1}
	three_smoothed_file_names = ds.smoothed.filenames(statedict=current_dict, card='==3')

	# get the smoothed entities filenames:
	smoothed_pth = ds.smoothed.path()

	# get a list of subjects ids: this would retrieve all the 'sub' key values
	subjects_ids = ds.subjects.values()
	['00', '01', '02', '03'], or list of values...

	






