i am building a resturant order management ai agent system using langgraph

i will explain you very clearly what i want and what is the architecture. i will also explain you the nodes the state and the edges
in the end i will give you test cases to simulate and to tell me whether they pass or fail 

The rought plan is :
there will be auser. when the code runs the user will give an order. this will be taken as an input which i will type 
this order should go to the llm the order as of now should contain the dish and the quantity
for simppicity purpose for now we will limit the order to one particular dish and whatever quantity the user wants
the llm will have to ectract the order name and the quantity from the user input
if the user inout is unrelated to food ordering the llm should not process that anf tell the user the same thing that this is an ai food ordering and niot th general purpose llm

once the llm has ordr the dish and quantity
it will send that to a node called order_confirmed
the task of order_confirmed is to look at the menu(i will tell you the menu later in the this prompt)

then this will decide one of 3 cases
the order is available
the order is partially ab=vailable
the order is not available at all(dis beiing not present in the menu or quantity is 0)
it will put this in the status of the state( i will tell you the exact content of the langraph state as well)

once the llm received this
if the status is confirmed(full available) it should call another node called cook

if the status is partial or unavailable it should again prompt the user to desice 
the user can either place a new order or can confim if he wants to go ahead with the partial order 

this order retires will be limited to 3 attempts if after the user is not satisified the system will coe to the end node

now when the cook node is called there an be 2 cases
either the cook is done then the status will be ready
and if the cook fails (we can use a probability function) - give 40% chance of fail and 60% chane of success

if the cook fails , there should be 1 mode attemt to allowed for cook to succeed. if the cook fails even after these then the llm should issue a aplogy to the user and come to end state

id the cook succeed the status will be ready and the nxt node will called will be serve

similar to cook this also gas 2 cases
server pass or server fail
thia also has 2 retry attempt
if the serve fails 2 time then the llm should issue a aplogy to the user and come to end state

if the serve succed the status should complete and the llm should issue a message to the user saying your order us complete
if serve fails then cook should ce called one more time to retry 
Note that if cook has exhausted the retry attempt then it should not cook again and allm should issue an apalogy and come to end state

Now the state of langraph

there should be a annoted message between llm and user 

there should be order details
dish name as string
required quantity as int
available quantity as int
order_confirmed will write the available quantity by reading the menu
the llm should get to know the order confirm status by reading the state
if the dish is not available in the menu the order_confirmed should write 0 as available quantity

the there should be status 
each node will update the sttaus as specified in the above rules
then order retrty attempt are 3
cook retry attempt 2
serve retry attempt are 2
each time a failure happens and a node is retrying it should decrement the counter
if any retry counter is 0 it means it is over 
llm should understand whether it has to give a retry or issue a appology by reading the counter 
int he end there should be final result whether order was completed ot not 

write the code and ask if there is any ipen questions from your side then ask
i will give you some test scnarios to test later on 