from bs4 import BeautifulSoup
import requests
import logging
from datetime import datetime
import pandas as pd
import os

time_out_minutes = 5
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def could_be_integer(in_strg):
    try:
        int(in_strg)
        return True
    except ValueError:
        logger.error(f"Appraisal area ids must be convertible to integers.  Check {in_strg} and try again")
        return False


def request_page(url_guess):
    logger.info(f"Trying url {url_guess}.")
    house_hca = requests.get(url=url_guess)
    if house_hca.status_code == 200:
        logger.info(f"Found url.")
        return house_hca.text
    else:
        logger.info("Failed to find page.")
        return ""


def convert_to_float(comma_string):
    return float(comma_string.replace(',', ''))


def guess_url(other_parcel_id):
    """
    Guesses a URL for a parcel_id summary page
    :param other_parcel_id:  string, any HCA parcel id.
    :return: the URL string for that parcel's summary
    """
    for year in range(2024, 2019, -1):
        year = str(year)
        logger.info(year)
        url_guess = f'https://wedge.hcauditor.org/view/re/{other_parcel_id}/{year}/summary'
        logger.info(url_guess)
        house_hca = requests.get(url=url_guess)
        if house_hca.status_code == 200:
            logger.info(f"Found parcel id {other_parcel_id} page with year {year}")
            return house_hca.text
    # if you get here and have not returned anything, say that
    logger.warning(f"Could not find parcel id {other_parcel_id} in Hamilton County summary pages.")
    return ''


def parse_property_overview(soupe):
    property_overview = (soupe.find('div', id='property_overview_wrapper')).find('tbody')
    ct = 0
    key = ""
    home_data_dict = {}
    for x in property_overview.find_all('td'):
        if ct % 2 == 0:
            key = x.text
        else:
            home_data_dict[key] = x.text
        ct += 1
    return home_data_dict


def add_data(other_parcel_id):
    """
    Scrapes a page dedicated to just this parcel and should be able to add acreage, # of brs, # of rooms
    :param other_parcel_id: the real parcel ID
    :return: a dictionary with keys as variable names and values for this individual property
    """
    other_parcel_id = other_parcel_id.replace('-', '')
    house_page = guess_url(other_parcel_id=other_parcel_id)
    if len(house_page) > 0:
        soup = BeautifulSoup(house_page, 'lxml')
        add_dict = parse_property_overview(soupe=soup)
        return add_dict
    return None


def collect_my_comps(area_id, additional_info: bool):
    """
    Pulls Hamilton County Auditor sales of comparable properties page and
    if possible, adds additional data (like acreage) summarizes
    :param area_id: Your property's appraisal area ID
    :param additional_info:  Boolean, True means to scrape EVERY comparable's description
    :return: pandas dataframe, one obs per sale with the transfer date, sales price
    # of properties is important
    # -- one sale price will be WAY TOO HIGH if the purchase included other properties
    # Property class, too.
    # -- SINGLE FAMILY in HCA is code 510.
    """
    price_summary = request_page(f"https://wedge.hcauditor.org/sales_report/{area_id}")

    soup = BeautifulSoup(price_summary, 'lxml')
    new_cols = ['Parcel Number', 'Transfer Date', 'Sales Price', 'Total Market Value',
                'Address', '# of Properties', 'Property Class Code']
    new_cols = [x.replace(' ', '_') for x in new_cols]
    data_list = []
    first = True
    added_columns = []
    found_comps = False
    stop_adding = False
    start_time = datetime.now()

    for obs in soup.find('tbody').find_all('tr', class_="center"):
        found_comps = True
        data = [x.text for x in obs.find_all('td')]
        new_data = [data[0], datetime.strptime(data[1], '%m/%d/%Y'),
                    convert_to_float(data[2]), convert_to_float(data[3]),
                    f"{data[4]} {data[5]}",
                    int(data[6]), int(data[7])]
        if additional_info and ((datetime.now() - start_time).seconds < (time_out_minutes * 60)):
            # additional data in dictionary
            add_dict = add_data(data[0])
            if add_dict is not None:
                if first:
                    added_columns = list(add_dict.keys())
                    new_cols = new_cols + added_columns
                    first = False
                additional_data = [add_dict[x] for x in added_columns]
            else:
                logger.warning("No additional data.")
                additional_data = [None for _ in added_columns]
            new_data += additional_data
        else:
            stop_adding = True

        data_list.append(new_data)
    if stop_adding:
        logger.warning(
            f"Add data timed out at {time_out_minutes} minutes. Only the top properties will have addl data.")
        logger.info("You can control the time out minutes, search for time_out_minutes.")

    if found_comps:
        df = pd.DataFrame(data=data_list, columns=new_cols)
        return df
    logger.warning(f"Could not find comparable sales for area id {area_id}.  Check and try again.")
    return None


def get_data_and_write(area_id, to_folder, property_type=510, extra_scraping=False):
    """
    Pulls the HCA comparable sales,
    adds potentially helpful descriptors and
    writes raw and filtered / aggregated files
    :param area_id: your Appraisal Area id
    :param to_folder: writes two files to this
    :param property_type: code for comparable property to yours.  defaults to single family
    :param extra_scraping: Bool, scrape the page of every comparable to get additional variables
            This data will be only in the raw file, not the aggregated
            And Scraping all pages is SLOW!!
    :return: aggregated (monthly) and filtered (single purchase, your property type) df
    """

    if could_be_integer(area_id):
        df = collect_my_comps(area_id=area_id, additional_info=extra_scraping)
        if df is not None:
            df.to_csv(os.path.join(to_folder, "raw_comps.csv"), index=False)
            # filter multi family
            df = df[df.Property_Class_Code == property_type]
            # filter single sales
            df = df[df['#_of_Properties'] == 1]
            df = df.sort_values('Transfer_Date')
            df['month'] = df.Transfer_Date.dt.month
            df['year'] = df.Transfer_Date.dt.year
            df_trend = df.groupby(['month', 'year']).agg({'Sales_Price': 'mean', 'Parcel_Number': 'count'})
            df_trend.to_csv(os.path.join(to_folder, "aggregated_comps.csv"))
            return df_trend
        return None
    return None


def find_my_area_id(my_parcel_id):
    """
    Uses a parcel id to search Hamilton County Auditor's page for an Appraisal Area
    :param my_parcel_id: string, the parcel id with hypens included
    :return: a five digit string containing the appraisal area code
    """
    my_parcel_id = my_parcel_id.replace('-', '')
    house_page = guess_url(other_parcel_id=my_parcel_id)
    if len(house_page) > 0:
        soup = BeautifulSoup(house_page, features="lxml")
        td_soup = soup.find_all("td")
        for one_td in td_soup:
            if one_td.div is not None:
                if one_td.div.string == "Appraisal Area":
                    appraise_area = one_td.find_all('div')[1].string[0:5]
                    return appraise_area
    logger.error("Parcel ID not found!")
    return None


def id_comps_pull_and_save(parcel_id, my_folder, add_scraping):
    """
    Using your parcel ID and the HCA website, pull the *same set of comparibles that HC uses.
    Save the raw file to my_folder
    :param parcel_id: string, my HCA parcel id
    :param my_folder: string, local folder where code will save agg and disagg df
    :param add_scraping: boolean, True if user wants # of brs and rooms, acreage etc., added.  (SLOW)
    :return: a Pandas dataframe aggregated to month/year with the average selling price of single family homes
    """
    appraisal_area_id = find_my_area_id(parcel_id)
    if appraisal_area_id is not None:
        logger.info(f"Success! Found your appraisal area code for HCA: {appraisal_area_id}.")
        df_agg = get_data_and_write(area_id=appraisal_area_id, to_folder=my_folder, extra_scraping=add_scraping)
        return df_agg
    return None


if __name__ == '__main__':
    # this will figure out your appraisal area,
    #  -pull all the HCA sales for that,
    #  -add predictors (slowly, time out constant at top) if you want, output as raw
    #  -filter on single family/ single sale, group by month, output as aggregate

    parcel_id = "179-0075-0011-00"  # '500-0353-0057-00'

    # folder for the two output files, raw (with extra variables) and aggregated to month
    file_location = '~'
    """"Do you want to WAIT an hour while I scrape websites
        to add acreage and # rooms / bedrooms to the raw file? y/n:
        """
    scrape_all = True
    agg_df = id_comps_pull_and_save(parcel_id=parcel_id, my_folder=file_location, add_scraping=scrape_all)
