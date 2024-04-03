from manifest import cluster_heads
from functions import * 


if __name__ == '__main__':
    interval = sys.argv[1]
    interval = int(interval)
    
    print("MAIN SERVER")
    time.sleep(10)
    ClusterHead1 = MainServer(main_server[0], main_server[1], id = 1, buffer_size = 20, send_interval=interval) 
    ClusterHead1.start_server()
    
