# contest_property_value
Simple python code to help people evaluate and potentially contest property values (in Hamilton Co, OH).

A wee bit of python code with which I successfully contested a **dramatic increase** to my property value.  It's not fancy, but I hope it will help others.  

The Hamilton County (Ohio) Auditor's Website keeps track of the full history of sales of real estate property *as well as* a list of comparible properties that the County uses to determine property values.  

If one has a property value increase, the rules suggest that one can ONLY use sale prices to argue against that.  So this code will pull the exact same list that the county uses so that you can run your own analyses on it.  It will also (if you tell it to) troll through all of those comparables and gather information like the number of bedrooms, rooms or the acreage.  THIS OPTION CAN BE SLOW if you have a lot of comparible properties.  There is a time-out constant at the top of the file which is in *minutes*.   

## Caveats
This will obviously only work in Hamilton County, but I would love to improve it.
I am not telling you what to do WITH the data pulls that this generates, though I have some models that I will likely check in.

In some neighborhoods, the houses are far enough apart, and/or the sales or so infrequent, that there really isn't enough data to analyze by month.  My apologies to those folks.   The county itself uses only these past four years and only within 0.5 miles of the home (I believe).   

# To Use This Code

Search for your own property's Parcel ID, and enter it as a string, with hyphens.  Pick a folder on your computer where you want the code to save the outputs; and decide whether you want the additional data in the raw file.  (It obviously cannot be in the aggregated file.)  

Open the file "sales_site_parser," scroll to the bottom and enter your choices.  Run that file and look in the folder you selected for Aggregated_comps.csv and raw_comps.csv.  
 
