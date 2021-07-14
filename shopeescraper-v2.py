import asyncio
import requests
import aiohttp
import sys
import time

#tuple of interested fields
INTERESTED_FIELDS = ('itemid', 'shopid', 'is_official_shop', 'name', 'price', 'item_rating', 'sold', 'historical_sold', 'shopee_verified')
#dict of proper ctime
ctime_milestone = {'ctime_6': 1610230711, 'ctime_1': 1622000000, 'ctime_12': 1595098010, 'ctime_36': 1530000231}

def get_data_from_api(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://shopee.vn'
    }   
    r = requests.get(url, headers = headers)
    data = r.json()
    return data

async def get_request(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://shopee.vn'
    }   
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
    return data

async def rate_user(data_list):
    if data_list:
        point = 0
        for data in data_list:
            if data['ctime'] <= ctime_milestone['ctime_36']:
                point += 10
            elif data['ctime'] < ctime_milestone['ctime_12']:
                point += 7
            elif data['ctime'] < ctime_milestone['ctime_6']:
                point += 3
        return point/len(data_list)
    return 0

async def get_request_user(ratings):
    if len(ratings) > 0:
        tasks = []
        for comment in ratings:
            url = 'https://shopee.vn/api/v4/shop/get_shop_detail?shopid='+str(comment['author_shopid'])
            try:
                task = asyncio.ensure_future(get_request(url))
            except:
                continue
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        data_list = []
        for result in results:
            if result['error']==0:
                data_list.append(result['data'])
        return data_list 
    return None

async def get_request_shop(shopid):
    url =  'https://shopee.vn/api/v2/shop/get?shopid='+str(shopid)
    data = await get_request(url)
    return data['data']

async def rate_shop(data):
    point = 0
    if data['account']['email_verified']:
        point += 0.5

    if data['account']['phone_verified']:
        point += 0.5

    if data['is_official_shop']:
        point += 3  

    if data['ctime'] <= ctime_milestone['ctime_36']:
        point += 2
    elif data['ctime'] < ctime_milestone['ctime_12']:
        point += 1
    elif data['ctime'] < ctime_milestone['ctime_6']:
        point += 0.25
    
    rating_sum = data['rating_good'] + data['rating_bad'] + data['rating_normal'] 
    if rating_sum >= 1000:
        point += 2
    elif rating_sum >= 500:
        point += 1
      
    if data['rating_star'] >= 4.5:
        point += 2
    elif data['rating_star'] >= 4:
        point += 0.5

    return point
    


async def get_request_rating(item_list):
    count = 0
    tasks = []
    for item in item_list:
        count+=1
        print('Retrieving info of item '+str(count))

        url = 'https://shopee.vn/api/v2/item/get_ratings?itemid='+str(item['itemid'])+'&limit=20&shopid='+str(item['shopid'])
        # data = get_data_from_api(url1)
        task = asyncio.ensure_future(get_request(url))
        tasks.append(task)
    ratings = await asyncio.gather(*tasks, return_exceptions=True)            
    if len(item_list) == len(ratings):
        for i in range(len(item_list)):
            item_list[i].update({'ratings': ratings[i]['data']['ratings']}) 
    else:
        print('Error in retrieving data...Quit program...')
        sys.exit()
    return item_list

    


async def main():
    start_time = time.time()
    search_keyword = str(input('What do you want to search on shopee: '))
    url = 'https://shopee.vn/api/v2/search_items/get?keyword='+search_keyword+'&limit=30'
    data = get_data_from_api(url)
    item_list=[]
    for i in range(len(data['items'])):
        new_item={}
        for key,value in data['items'][i].items():
            if key in INTERESTED_FIELDS:
                new_item.update({key:value})
        if new_item['item_rating']['rating_star'] < 3.5 or new_item['item_rating']['rating_star'] is None:
            continue
        else:
            item_list.append(new_item)

    # get rating from item_list
    print('*********************')
    print(f'The search result has {len(item_list)} items')
    item_list = await get_request_rating(item_list)
    print('\n')

    for item in item_list:
        print(f'Calculating point for {item["name"]}')
        shop_point =  await rate_shop(await get_request_shop(item['shopid']))
        user_point =  await rate_user(await get_request_user(item['ratings']))
        final_point = round((shop_point + user_point)/2, 2)
        item.update({'final_point':final_point})
        item.update({'shop_point':shop_point})
        item.update({'user_point':user_point})

    final_list = sorted(item_list, key=lambda k: k['final_point'], reverse=True)
    
    duration = time.time() - start_time

    #print out final rank
    print('\n')    
    print("----------------------------")
    print('This is the final result: \n')
    for item in final_list:
        print(str(item['shop_point']) + ' ||| ' + str(item['user_point']) + ' ||| ' + str(item['final_point']) + ' ||| ' + item['name'])

    print('---------END OF PROGRAM------------')
    print(f'The program took {duration}s to finish.')

if __name__=='__main__':
    asyncio.run(main())
        