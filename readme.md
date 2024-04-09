# README

Note that the simulation code was configured for Apple Silicon Macbooks hence the simulation scripts may not run for Windows or Linux due to the difference in terminals.

## Virtual Environment Setup

1. 
```
python3 -m venv virtualenv
```
2. 
```
source virtualenv/bin/activate
```
3. 
```
pip install -r requirements.txt
```

## Running simulations
The simluations are configured as follows: 
1. One to One relationship between sensor and cluster. Only 1 try for sending. If packet lost then no resending. 

2. One to one, 2 tries.

3. One to One, 3 tries.

4. One to two, each sensor sends to 2 clusters. 2 tries. 

5. One to three. 2 tries.

Following this we found that the pkt success rate was over 95% consistently. Hence we repeated the 5th simulation but with larger configurations.

6. One to three, 2 tries. 10 sensors, 5 clusters, 1 server. 

7. One to three, 2 tries. 50 sensors, 5 clusters, 1 server. 



You may refer to the screenshots in the ./simulation_results folder. The images are labelled based on the simulation number