
import requests
import sys
import argparse
import tinydb
from jinja2 import Environment, PackageLoader

# limit requests because of throttling ban
PAGE_SIZE=50
MAX_RESULTS=500
LOCAL_DATA='data/stats.json'

# for clarity
STACK_EXCHANGE_API='https://api.stackexchange.com/2.2'


class QuickStats:
    def __init__(self, site, data):
        self.site = site
        accepted = [x for x in data if x['is_accepted'] == True]
        self.accepted_count = len(accepted)


def query_resource(resource_name, params=None):
    api_url = "%s/%s" % (STACK_EXCHANGE_API,resource_name)
    response = requests.get(url=api_url, params=params)
    if response.status_code != 200:
        raise Exception(response.content)
    data = response.json()
    return data


def get_paged_answers(datefrom, dateto, site, page, page_size):
    paged_data = query_resource('answers', {'datefrom': datefrom,
                                        'dateto': dateto,
                                        'site': site,
                                        'order': 'desc',
                                        'sort': 'activity',
                                        #'page': page,
                                        #'page_size': page_size
                                        })
    return paged_data


def retrieve_data(args):
    """
    :param args: command line arguments
    :return: a list of rows for all answers in the specific range
    """
    data = []
    page=1
    paged_data = get_paged_answers(args.datefrom, args.dateto, args.site, page, page_size=PAGE_SIZE)
    while paged_data['has_more'] == True:
        items = paged_data['items']
        data.extend(items)
        if len(data) >= MAX_RESULTS:    # or len(items) < PAGE_SIZE:
            break
        page += 1
        paged_data = get_paged_answers(args.datefrom, args.dateto, args.site,page,page_size=PAGE_SIZE)

    return data


def load_data():
    """
    make debug easier since API has data throttling
    :return:
    """
    db = tinydb.TinyDB(LOCAL_DATA)
    table = db.table('quick_stats')
    rows = table.all()
    db.close()
    return rows[0]['data']


def store_data(data):
    """
    make debug easier since API has data throttling
    :param data:
    :return:
    """
    db = tinydb.TinyDB(LOCAL_DATA)
    table = db.table('quick_stats')
    table.insert({'data': data})
    db.close()


def compute_stats(data):
    quick_stats = QuickStats(args.site, data)
    return quick_stats


def render_stats(quick_stats):
    env = Environment(loader=PackageLoader('app', 'templates'))
    template = env.get_template('quick_stats.jinja2.html')
    output = template.render(quick_stats = quick_stats)
    with open("output/quick_stats.html","w+") as f:
        f.write(output)
        f.flush()


def run_script(args):
    if args.localdata and eval(args.localdata):
        data=load_data()
    else:
        data = retrieve_data(args)
        store_data(data)

    quick_stats=compute_stats(data)
    render_stats(quick_stats)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--datefrom', dest='datefrom')
    parser.add_argument('--dateto', dest='dateto')
    parser.add_argument('--site', dest='site')
    parser.add_argument('--localdata', dest='localdata')
    args = parser.parse_args(sys.argv[1:])
    try:
        run_script(args)
    except Exception as x:
        print x.message