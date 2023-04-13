#!/usr/bin/env python

import pandas as pd
from functools import reduce
import requests
import json
#https://unipept.ugent.be/apidocs/taxonomy

def get_taxname(tax_id,tax_level):
    tags = {"S": "species_name",
            "G": "genus_name",
            "F": "family_name",
            "O": "order_name",
            "C": "class_name",
            "A": ["superkingdom_name", "phylum_name", "class_name", "order_name", "family_name", "genus_name", "species_name"]
            }
    tax_level_tag = tags[tax_level]
    #Avoids pipeline crash due to "nan" classification output. Thanks to Qi-Maria from Github
    if str(tax_id) == "nan":
        tax_id = 1
    
    path = 'http://api.unipept.ugent.be/api/v1/taxonomy.json?input[]=' + str(int(tax_id)) + '&extra=true&names=true'
    complete_tax = requests.get(path).text

    #Checks for API correct response (field containing the tax name). Thanks to devinbrown from Github
    try:
        if isinstance(tax_level_tag, (list, tuple)):
             names = [json.loads(complete_tax)[0][tag] for tag in tax_level_tag]
             if name == "":
                name = json.loads(complete_tax)[0]["taxon_name"]
             name = ';'.join(names)
        else:
            name = json.loads(complete_tax)[0][tax_level_tag]
            if name == "":
                name = json.loads(complete_tax)[0]["taxon_name"]
    except:
        name = str(int(tax_id))

    return name

def get_taxname_from_dmp(data, tax_id, tax_level):
    tags = {"S": "species","G": "genus","F": "family", "O": "order"}
    tax_level_tag = tags[tax_level]

    if str(tax_id) == "nan":
        tax_id = 1

    name = data.loc[data['taxid'] == tax_id, tax_level_tag].iloc[0]
    if type(name) != str:
        name = data.loc[data['taxid'] == tax_id, "name"].iloc[0]
        if type(name) != str:
            name = data.loc[data['taxid'] == tax_id, "sciname"].iloc[0]

    return name


def get_abundance_values(names,paths):
    dfs = []
    for name,path in zip(names,paths):
        data = pd.read_csv(path, index_col=False, sep=';').iloc[:,1:]

        total = sum(data['reads_in_cluster'])
        rel_abundance=[]

        for index,row in data.iterrows():
            rel_abundance.append(row['reads_in_cluster'] / total)
            
        data['rel_abundance'] = rel_abundance
        dfs.append(pd.DataFrame({'taxid': data['taxid'], 'rel_abundance': rel_abundance, 'reads': data['reads_in_cluster']}))
        data.to_csv("" + name + "_nanoclust_out.txt")

    return dfs, data

def merge_abundance(dfs, data, tax_level):
    df_final = reduce(lambda left,right: pd.merge(left,right,on='taxid',how='outer').fillna(0), dfs)
    all_tax=[]
    for index, row in df_final.iterrows():
        try:
            all_tax.append(get_taxname_from_dmp(data, row["taxid"], tax_level))
        except:
            all_tax.append(get_taxname(row["taxid"], tax_level))
    df_final["taxid"] = all_tax
    #df_final["taxid"] = [get_taxname(row["taxid"], tax_level) for index, row in df_final.iterrows()]
    df_final_grp = df_final.groupby(["taxid"], as_index=False).sum()
    df_final_sorted = df_final_grp.sort_values(by='rel_abundance', ascending=False)
    return df_final_sorted

def get_abundance(names,paths,tax_level):
    if(not isinstance(paths, list)):
        paths = [paths]
        names = [names]

    dfs, data = get_abundance_values(names,paths)
    df_final_grp = merge_abundance(dfs, data, tax_level)
    df_final_grp.to_csv("rel_abundance_"+ names[0] + "_" + tax_level + ".csv", index = False)

paths = "$table"
names = "$barcode"

get_abundance(names,paths, "G")
get_abundance(names,paths, "S")
get_abundance(names,paths, "O")
get_abundance(names,paths, "F")
