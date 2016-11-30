
import requests
import os
import sys
import argparse
import moment
import tinydb
import time
import datetime
import json
import itertools
from jinja2 import Environment, PackageLoader

# limit requests because of throttling ban
PAGE_SIZE = 100
MAX_RESULTS = 500
LOCAL_DATA = 'data/stats.json'

# for clarity
STACK_EXCHANGE_API = 'https://api.stackexchange.com/2.2'
DATE_FORMAT = "%Y-%m-%d"


class QuickStats:
    def start_compute(self, site, all_answers, top10_answers):
        self.site = site
        self.total_count = len(all_answers)

        # extract accepted answers
        answers_accepted = [x for x in all_answers if x['is_accepted'] is True]

        # compute 'accepted answers count'
        self.accepted_count = len(answers_accepted)

        # compute 'average score' of accepted answers
        self.accepted_average_score = sum( [y['score'] for y in answers_accepted] ) / (self.accepted_count if self.accepted_count > 0 else 0)

        # group answers per question
        group_by_question = list(map(lambda x: { 'question_id': x[0], 'answers' : list(x[1]) }, itertools.groupby(all_answers, lambda z: z['question_id'])))
        question_count = len(group_by_question)
        answer_count = sum( [ len(g['answers']) for g in group_by_question ]  )
        self.average_answers_per_question = answer_count / ( question_count * 1.0)

    def end_compute(self,start_time):
        self.time_elapsed = time.clock() - start_time


def query_resource(resource_name, params=None):
    """
    a simplified REST call per resource
    :param resource_name: the REST resource
    :param params: extra query params
    :return: a json response
    """
    api_url = "%s/%s" % (STACK_EXCHANGE_API,resource_name)
    response = requests.get(url=api_url, params=params)
    if response.status_code != 200:
        raise Exception(response.content)
    data = response.json()
    return data


def get_paged_answers(datefrom, dateto, site, page, page_size,sort_by='activity'):
    """
    Since the API does not returns the total size, we have to repeatdely
    get the results until no more data is returned
    :param datefrom:
    :param dateto:
    :param site:
    :param page:
    :param page_size:
    :return:
    """
    paged_data = query_resource('answers', {'datefrom': datefrom,
                                        'dateto': dateto,
                                        'site': site,
                                        'order': 'desc',
                                        'sort': sort_by,
                                        'page': page,
                                        'page_size': page_size
                                        })
    return paged_data


def to_unix_epoch(date):
    date_m = moment.date(date, DATE_FORMAT)
    date = datetime.date(date_m.year, date_m.month, date_m.day)
    return  date.strftime("%s")


def retrieve_all_answers(site, datefrom, dateto):
    """
    retrieve data from API
    :return: a list of rows for all answers in the specific range
    """
    data = []
    page = 1
    paged_data = get_paged_answers(datefrom, dateto, site, page, page_size=PAGE_SIZE)
    while paged_data['has_more']:
        items = paged_data['items']
        data.extend(items)
        # save in every step, avoid loosing data in case of throttling exception
        store_data(data)

        if MAX_RESULTS > 0 and len(data) >= MAX_RESULTS:
            break
        page += 1
        paged_data = get_paged_answers(datefrom, dateto, site, page, page_size=PAGE_SIZE)

    return data


def load_from_local_file():
    """
    load data from file in case of throttling ban, used to make debugging easier
    :return:
    """
    with open(LOCAL_DATA,"r") as f:
        content = f.read()
        data = json.loads(content)
        return data


def store_data(data):
    """
    make debug easier since API has data throttling
    :param data:
    :return:
    """
    with open(LOCAL_DATA,"w+") as f:
        content = json.dumps(data)
        f.write(content)
        f.flush()


def render_stats(quick_stats):
    env = Environment(loader=PackageLoader('app', 'templates'))
    template = env.get_template('quick_stats.jinja2.html')
    output = template.render(quick_stats = quick_stats)
    with open("output/quick_stats.html","w+") as f:
        f.write(output)
        f.flush()


def compute_stats(args):
    start_time = time.clock()

    datefrom_unix = to_unix_epoch(args.datefrom)
    dateto_unix = to_unix_epoch(args.dateto)

    if args.localdata and eval(args.localdata):
        all_answers = load_from_local_file()
    else:
        all_answers = retrieve_all_answers(args.site, datefrom_unix, dateto_unix)

    top10_answers = get_paged_answers(datefrom_unix, dateto_unix, args.site, 1, page_size=10, sort_by='score')

    quick_stats = QuickStats()
    quick_stats.start_compute(args.site, all_answers, top10_answers)
    quick_stats.end_compute(start_time)

    render_stats(quick_stats)


def create_dir_if_not_exists(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--datefrom', dest='datefrom')
    parser.add_argument('--dateto', dest='dateto')
    parser.add_argument('--site', dest='site')
    parser.add_argument('--localdata', dest='localdata')
    args = parser.parse_args(sys.argv[1:])
    try:
        create_dir_if_not_exists('data') # store json results
        create_dir_if_not_exists('output') # store html output
        compute_stats(args)
    except Exception as x:
        print x.message
