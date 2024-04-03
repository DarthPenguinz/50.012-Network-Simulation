from manifest import cluster_heads, main_server
from functions import * 


if __name__ == '__main__':
    idx = sys.argv[1]
    idx = int(idx)
    print("HOST ID: ", idx)
    time.sleep(10)
    ClusterHead1 = ClusterHead(idx, cluster_heads[idx][0], cluster_heads[idx][1], main_server[0], main_server[1]) 
    ClusterHead1.start_server()