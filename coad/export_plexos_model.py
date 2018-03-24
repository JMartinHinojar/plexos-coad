import sys
import pandas as pd
import os
import argparse

#####
# export the data associated with a plexos input model and write as accessable csv files
#
# USAGE:
#  import coad.COAD as plx
#  plx_mod = plx.COAD('RTS-GMLC.xml')
#  objects,scenarios,data_files,models = plx.export_plexos_model.get_model_items(plx_mod,models=['DAY_AHEAD'])
#  data = plx.export_plexos_model.export_data(plx_mod,scenarios,objects,data_files,models)
#  plx.export_plexos_model.write_tables(data,folder='./')

def get_model_items(coad,models, filter_val = '',filter_cls = 'Region'):
    
    if filter_val != '':
        try:
            regions = [coad[filter_cls][filter_val]]
        except:
            if filter_cls=='Region':
                filter_cls = 'Zone'
            else:
                filter_cls = 'Region'
            
        try:
            regions = [coad[filter_cls][filter_val]]
        except:
            regions = ['']
            print('Cannot find filter in Regions or Zones')
    else:
        regions = ['']
    

    objects = []
    scenarios = []

    if models == ['']:
        sys.exit('Please specify a model to export')
        
    for mod in models:
        #all possible objects in a PLEXOS model
        all_fields = set(coad.keys())

        #objects with explicitly defined memberships to the model
        all_children = set([o.hierarchy for o in coad['Model'][mod].get_children()])

        #scenarios to gather
        scen = set([o.hierarchy for o in coad['Model'][mod].get_children('Scenario')])
        scenarios.extend([i.split('.',1)[1] for i in scen])

        #objects with model membership (without scenarios)
        settings = all_children-scen

        #parameters = [i.split('.',1)[0] for i in settings]
        #settings = [i.split('.',1)[1] for i in settings]

        for s in settings:
            objects.append({'cls': s.split('.',1)[0],
                                'name': s.split('.',1)[1]})
    

    #get all the data files associated with the scenarios
    data_files = coad['Data File'].keys()
    for data_file in coad['Data File'].values():
        objects.append({'cls': data_file.get_class().meta['name'],
                        'name': data_file.meta['name']})


    #get all relatives of filter region/zone
    if regions == ['']:
        regions = coad[filter_cls].values() # + coad['Zone'].values()

    for r in regions:
        #print(filter_cls + ':  ' + r.meta['name'])
        for p in r.get_parents():
            #print('    parent: ' + p.meta['name'])
            objects.append({#'relationship': 'parent',
                                'cls': p.get_class().meta['name'],
                                'name': p.meta['name']})
                                #,'obj': p})
            if p.meta['name'] != 'System':
                for pp in p.get_children():
                    objects.append({#'relationship': 'child',
                                'cls': pp.get_class().meta['name'],
                                'name': pp.meta['name']})
                                #,'obj': pp})
            for pp in p.get_parents():
                objects.append({#'relationship': 'parent',
                            'cls': pp.get_class().meta['name'],
                            'name': pp.meta['name']})
                            #,'obj': pp})
                    
                    
    print('Done Collecting Objects, removing duplicates...')
    # drop the duplicates
    objects = pd.DataFrame(objects).drop_duplicates().reset_index(drop=True) #.T.to_dict().values()
    print('Done')
    return(objects,scenarios,data_files,models)


def export_data(coad, scenarios, objects,data_files,models):
    d = []
    
    nobj = len(objects)
    for index, row in objects.iterrows():
        #clear_output()
        #print('{0}/{1}'.format(index,nobj))
        obj_class = row['cls']
        obj_name = row['name']
        if not(obj_class=='System' and obj_name=='System'):
            obj = coad[obj_class][obj_name]
            if obj.keys():
                for atr, val in obj.items():
                    d.append({'cls': obj_class,
                                         'object': obj_name,
                                         'property': atr,
                                         'value': val})
            #relationships
            all_children = set([o.hierarchy for o in obj.get_children()])
            all_parents = set([o.hierarchy for o in obj.get_parents()])
            children = all_children - all_parents
            parents = all_parents - all_children
            peers = all_children & all_parents

            #parents
            if len(parents):
                for p in parents:
                    p_cls, p_val = p.split('.')
                    if (p_cls == 'Model' and p_val in models) or p_cls != 'Model':
                        d.append({'cls': obj_class,
                                         'object': obj_name,
                                         'property': p_cls,
                                         'value': p_val})
            #peers
            if len(peers):
                for p in peers:
                    p_cls, p_val = p.split('.')
                    d.append({'cls': obj_class,
                                     'object': obj_name,
                                     'property': p_cls,
                                     'value': p_val})
            #children
            if len(children):
                for p in children:
                    p_cls, p_val = p.split('.')
                    d.append({'cls': obj_class,
                                     'object': obj_name,
                                     'property': p_cls,
                                     'value': p_val})

            # Properties
            props = obj.get_properties()
            prop_keys = sorted(props)
            if len(prop_keys):
                for pkey in prop_keys:
                    [prop_type,prop_name] = pkey.split('.')
                    vkeys = sorted(props[pkey])
                    read = False
                    scenario_tag = ''
                    datafile_tag = ''
                    if prop_type =='Scenario':
                        if prop_name in scenarios:
                            read = True
                            scenario_tag = prop_name
                    if prop_type == 'Data File':
                        if prop_name in data_files:
                            read = True
                            datafile_tag = prop_name
                    if prop_type == 'System':
                        read = True
                    if read == True:
                        for vkey in vkeys:
                            if vkey != 'uid':
                                d.append({'cls': obj_class,
                                                 'object': obj_name,
                                                 'property': vkey,
                                                 'scenario': ','.join(str(x) for x in [scenario_tag,datafile_tag] if x!=''),
                                                 'value': props[pkey][vkey]})

            # Text
            props = obj.get_text()
            prop_keys = sorted(props)
            if len(prop_keys):
                for pkey in prop_keys:
                    [cat,name] = pkey.split(".",1)
                    if (cat == 'Scenario' and name in scenarios) or (cat == 'Data File' and name in data_files) or cat == 'System':
                        for vkey in sorted(props[pkey]):
                            d.append({'cls': obj_class,
                                             'object': obj_name,
                                             'property': vkey,
                                             'scenario': pkey,
                                             'value': props[pkey][vkey]})
    
    d = pd.DataFrame(d)
    d.value = d.value.apply(lambda x: tuple(x) if type(x) is list else x)
    return(d)

def write_tables(data,folder=''):
    for cls in data.cls.unique():
        df = data.loc[data['cls']==cls].groupby(['object', 'property'])['value'].apply(lambda x: tuple(x)).reset_index()\
                .pivot(index='object', columns='property', values='value').fillna('')
        df.to_csv(os.path.join(folder,cls+'.csv'),index=False)


def main():
    """Parse args and process solution zipfile into hdf5
    """
    parser = argparse.ArgumentParser(description="Export csv files for a specific PLEXOS input model")

    parser.add_argument('-f', '--filepath', help='path to PLEXOS input .xml or .db')
    parser.add_argument('-m', '--models', help='list of models to export',default='')
    parser.add_argument('-c', '--filter_cls', help='optional-class of filter string, e.g. Region, Zone',default='')
    parser.add_argument('-n', '--filter_val', help='optional-name of region or zone to extract',default='')
    parser.add_argument('-o', '--output_folder', help='folder to output csv files')

    args = parser.parse_args()


    coad = COAD(args.filepath)
    objects, scenarios, data_files, models = get_model_items(coad,models=args.models,filter_cls=args.filter_cls,filter_val=args.filter_val)
    data = export_data(coad,scenarios,objects,data_files,models)
    write_tables(data,args.output_folder)


if __name__ == "__main__":
    main()