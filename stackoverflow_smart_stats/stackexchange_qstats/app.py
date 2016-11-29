
import requests
import sys
import argparse
import moment

DATE_FORMAT='%Y-%m-%d'
STACK_EXCHANGE_API='https://api.stackexchange.com/2.2'


class QuickStats:
    def __init__(self, site, data):
        self.site = site
        self.accepted_count = len( f for f in data if f['is_accepted'] == True)
        pass


def query_resource(resource_name, params=None):
    api_url = "%s/%s" % (STACK_EXCHANGE_API,resource_name)
    response = requests.get(url=api_url,params=params)
    if response.status_code != 200:
        raise Exception(response.content)
    data = response.json()
    return data


def get_paged_answers(datefrom, dateto, site, page, page_size=500):
    paged_data = query_resource('answers', {'datefrom': datefrom,
                                        'dateto': dateto,
                                        'site': site,
                                        'order': 'desc',
                                        'sort': 'activity',
                                        'page': page,
                                        'page_size': page_size})
    return paged_data


def compute_stats(args):
    data = []
    page=1
    paged_data = get_paged_answers(args.datefrom, args.dateto, args.site, page)
    while paged_data['has_more'] == True:
        data.append(paged_data.items)
        page += 1
        paged_data = get_paged_answers(args.datefrom, args.dateto, args.site,page)

    quick_stats = QuickStats(args.site, data.items)
    return  quick_stats

def run(args):
    quick_stats=compute_stats(args)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--datefrom', dest='datefrom')
    parser.add_argument('--dateto', dest='dateto')
    parser.add_argument('--site', dest='site')
    args = parser.parse_args(sys.argv[1:])
    try:
        run(args)
    except Exception as x:
        print x.message