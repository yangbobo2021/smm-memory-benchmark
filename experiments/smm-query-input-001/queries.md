# 257题原问题与两路独立输入

所有输入均在本轮排名前冻结。仅展示查询，不包含参考答案。

## P01

Did I finish reading 'The Nightingale' by Kristin Hannah?

BM25：`Nightingale Kristin Hannah finished finish reading read`

向量：Whether I finished reading The Nightingale by Kristin Hannah.

## P02

How many dozen eggs do we currently have stocked up in our refrigerator?

BM25：`egg eggs dozen refrigerator fridge stocked stock remaining`

向量：The current number of dozens of eggs stocked in our refrigerator, including changes to the stock.

## P03

How many issues of National Geographic have I finished reading?

BM25：`National Geographic issues issue finished read reading`

向量：The issues of National Geographic that I have finished reading and their total count.

## P04

How much did I earn at the Downtown Farmers Market on my most recent visit?

BM25：`Downtown Farmers Market earned earn earnings sales recent`

向量：How much I earned during my most recent visit to the Downtown Farmers Market.

## P05

How many hours have I spent on my abstract ocean sculpture?

BM25：`abstract ocean sculpture hours spent working`

向量：The hours I have spent working on my abstract ocean sculpture, including separate work sessions.

## P06

How many days a week do I attend fitness classes?

BM25：`fitness classes class attend attending weekly week schedule`

向量：My weekly fitness class attendance schedule and the distinct days I attend classes.

## P07

How many dinner parties have I attended in the past month?

BM25：`dinner parties party attended attend month`

向量：Dinner parties that I actually attended during the past month, rather than parties I only planned.

## P08

How many different types of citrus fruits have I used in my cocktail recipes?

BM25：`citrus fruit fruits cocktails cocktail recipes used`

向量：The different kinds of citrus fruit I actually used in my cocktail recipes.

## P09

How many days did I spend participating in faith-related activities in December?

BM25：`faith religious activities participated December`

向量：My participation in faith-related activities during December and the dates of those activities.

## P10

How many projects have I been working on simultaneously, excluding my thesis?

BM25：`projects project working simultaneously thesis`

向量：Projects I have been working on at the same time, excluding my thesis from the count.

## P11

I'm planning to visit the Vatican again and I was wondering if you could remind me of the name of that famous deli near the Vatican that serves the best cured meats and cheeses?

BM25：`Vatican deli cured meats cheeses`

向量：The previously discussed deli near the Vatican known for cured meats and cheeses, and its name.

## P12

I wanted to check back on our previous conversation about Netflix. I mentioned that I wanted to be able to access all seasons of old shows? Do you remember what show I used as an example, the one that only had the last season available?

BM25：`Netflix seasons season old shows available`

向量：The old show I used as an example when discussing Netflix having only the last season available.

## P13

I was looking back at our previous chat and I wanted to confirm, how many times did the Chiefs play the Jaguars at Arrowhead Stadium?

BM25：`Chiefs Jaguars Arrowhead Stadium played games`

向量：The number of Chiefs versus Jaguars games at Arrowhead Stadium discussed in our earlier conversation.

## P14

I was going through our previous conversation about the impact of the political climate in Catalonia on its literature and music. Can you remind me of the example you gave of a Spanish-Catalan singer-songwriter who supports unity between Catalonia and Spain?

BM25：`Catalonia Spain unity singer songwriter political literature music`

向量：The Spanish-Catalan singer-songwriter supporting unity between Catalonia and Spain who was given as an example in our earlier discussion.

## P15

I'm planning my trip to Amsterdam again and I was wondering, what was the name of that hostel near the Red Light District that you recommended last time?

BM25：`Amsterdam hostel Red Light District recommended`

向量：The name of the hostel near Amsterdam's Red Light District that was recommended in our previous conversation.

## P16

How many skeins of worsted weight yarn did I find in my stash?

BM25：`worsted weight yarn skeins skein stash found`

向量：The number of skeins of worsted weight yarn I found in my stash.

## P17

How many largemouth bass did I catch on my fishing trip to Lake Michigan?

BM25：`Lake Michigan largemouth bass caught catch fishing`

向量：How many largemouth bass I caught on my fishing trip to Lake Michigan.

## P18

How much did I spend on a designer handbag?

BM25：`designer handbag bought purchased spent cost`

向量：The amount I spent buying a designer handbag.

## P19

Where did I buy my new tennis racket from?

BM25：`tennis racket bought purchased store shop`

向量：Where I purchased my new tennis racket.

## P20

What time do I stop checking work emails and messages?

BM25：`work emails messages stop checking evening cutoff`

向量：The time when I stop checking work emails and messages.

## P21

Who graduated first, second and third among Emma, Rachel and Alex?

BM25：`Emma Rachel Alex graduated graduation`

向量：The graduation dates of Emma, Rachel and Alex, to determine who graduated first, second and third.

## P22

How many weeks ago did I start using the cashback app 'Ibotta'?

BM25：`Ibotta cashback app started using`

向量：When I started using the Ibotta cashback app, to calculate how many weeks ago that was.

## P23

How many days passed between the day I repotted the previous spider plant and the day I gave my neighbor, Mrs. Johnson, a few cuttings from my spider plant?

BM25：`spider plant repotted repot cuttings neighbor Johnson`

向量：The date I repotted my previous spider plant and the date I gave spider plant cuttings to my neighbor Mrs. Johnson.

## P24

How many days ago did I attend a networking event?

BM25：`networking event attended attend date`

向量：The date I attended a networking event, to calculate how many days ago it was.

## P25

What time do I wake up on Tuesdays and Thursdays?

BM25：`wake waking up Tuesdays Thursdays Tuesday Thursday schedule`

向量：My wake-up times on Tuesdays and Thursdays, including changes to that schedule.

## L001

How many days did I spend in total traveling in Hawaii and in New York City?

BM25：`Hawaii New York City trip travel days`

向量：The durations of my trips to Hawaii and New York City, to add the days spent traveling in those two places.

## L002

How many bikes do I currently own?

BM25：`bike bikes bicycle bicycles own bought sold`

向量：How many bikes I currently own after any purchases or other changes.

## L003

Where do I initially keep my old sneakers?

BM25：`old sneakers kept keep stored initially originally`

向量：Where I initially kept my old sneakers, before any later move.

## L004

I mentioned that I participated in an art-related event two weeks ago. Where was that event held at?

BM25：`art event attended participated held location`

向量：The location of the art-related event I said I participated in two weeks ago.

## L005

What is the order of airlines I flew with from earliest to latest before today?

BM25：`airlines airline flew flown flights flight`

向量：The airlines I flew with and the dates of those flights, ordered from earliest to latest before today.

## L006

I mentioned cooking something for my friend a couple of days ago. What was it?

BM25：`friend cooked cooking made meal food`

向量：What I cooked for my friend a couple of days ago.

## L007

What did I do with Rachel on the Wednesday two months ago?

BM25：`Rachel Wednesday spent met together`

向量：What I did with Rachel on the Wednesday two months ago.

## L008

How many plants did I initially plant for tomatoes and cucumbers?

BM25：`tomato tomatoes cucumber cucumbers planted plants initially`

向量：The initial numbers of tomato plants and cucumber plants I planted.

## L009

How many years will I be when my friend Rachel gets married?

BM25：`Rachel wedding married marriage age birthday`

向量：My age when my friend Rachel gets married, using her wedding timing and my age information.

## L010

What was the social media activity I participated 5 days ago?

BM25：`social media participated activity challenge`

向量：The social media activity I participated in five days ago.

## L011

How many times did I bake something in the past two weeks?

BM25：`bake baked baking`

向量：Occurrences of things I actually baked during the past two weeks, to count separate baking occasions.

## L012

What is the order of the concerts and musical events I attended in the past two months, starting from the earliest?

BM25：`concert concerts musical events attended`

向量：Concerts and musical events I attended in the past two months, with dates to order them from earliest onward.

## L013

How long have I been collecting vintage cameras?

BM25：`vintage cameras camera collecting collected started`

向量：When I started collecting vintage cameras and how long I have been collecting them.

## L014

How many months have passed since I last visited a museum with a friend?

BM25：`museum visited visit friend months`

向量：The date of my most recent museum visit with a friend, to calculate how many months have passed.

## L015

What charity event did I participate in a month ago?

BM25：`charity charitable event participated attended`

向量：The charity event I participated in a month ago.

## L016

Which bike did I fixed or serviced the past weekend?

BM25：`bike bicycle fixed fix serviced service weekend`

向量：Which of my bikes I fixed or serviced during the past weekend.

## L017

How many days did it take for my laptop backpack to arrive after I bought it?

BM25：`laptop backpack bought ordered arrived delivered`

向量：When I bought my laptop backpack and when it arrived, to find the delivery time in days.

## L018

What was the significant buisiness milestone I mentioned four weeks ago?

BM25：`business milestone achieved reached`

向量：The significant business milestone I mentioned four weeks ago.

## L019

How often do I see my therapist, Dr. Smith?

BM25：`therapist Dr Smith appointments sessions frequency`

向量：How often I see my therapist Dr. Smith.

## L020

How much will I save by taking the train from the airport to my hotel instead of a taxi?

BM25：`airport hotel train taxi fare cost`

向量：The train and taxi fares from the airport to my hotel, to calculate the savings from taking the train.

## L021

How many days before I bought the iPhone 13 Pro did I attend the Holiday Market?

BM25：`Holiday Market iPhone 13 Pro bought attended`

向量：The date I attended the Holiday Market and the date I bought the iPhone 13 Pro.

## L022

I mentioned an investment for a competition four weeks ago? What did I buy?

BM25：`competition investment bought purchased`

向量：What I bought as an investment for a competition, as mentioned four weeks ago.

## L023

Which event happened first, my cousin's wedding or Michael's engagement party?

BM25：`cousin wedding Michael engagement party dates`

向量：The dates of my cousin's wedding and Michael's engagement party, to determine which occurred first.

## L024

How many days did it take me to finish 'The Nightingale' by Kristin Hannah?

BM25：`Nightingale Kristin Hannah started finished reading`

向量：When I started and finished The Nightingale by Kristin Hannah, to calculate the number of reading days.

## L025

How many engineers do I lead when I just started my new role as Senior Software Engineer? How many engineers do I lead now?

BM25：`Senior Software Engineer lead engineers team initially now`

向量：The number of engineers I led when I started my new Senior Software Engineer role and the number I lead now.

## L026

How many weeks ago did I meet up with my aunt and receive the crystal chandelier?

BM25：`aunt crystal chandelier met received`

向量：When I met my aunt and received the crystal chandelier, to calculate how many weeks ago it was.

## L027

How many pages do I have left to read in 'The Nightingale'?

BM25：`Nightingale pages read remaining total`

向量：My reading progress and the total length of The Nightingale, to determine the number of pages left.

## L028

Who did I meet with during the lunch last Tuesday?

BM25：`lunch Tuesday met person`

向量：Who I met for lunch last Tuesday.

## L029

What is the name of my cat?

BM25：`cat name named`

向量：The name of my cat.

## L030

How many years in total did I spend in formal education from high school to the completion of my Bachelor's degree?

BM25：`high school Bachelor degree education years graduated`

向量：The years I spent in high school and in my Bachelor's degree, to calculate the total formal education duration across those stages.

## L031

How many different museums or galleries did I visit in the month of February?

BM25：`museum museums gallery galleries visited February`

向量：The distinct museums or galleries I visited during February.

## L032

How much time do I dedicate to practicing guitar every day?

BM25：`guitar practice practicing daily minutes hours`

向量：The amount of time I spend practicing guitar every day.

## C001

Where did Deborah get married?

BM25：`Deborah married wedding ceremony location`

向量：Where Deborah got married.

## C002

When did John have a party with veterans?

BM25：`John party veterans date`

向量：When John had a party with veterans.

## C003

What is Nate's favorite dish from the cooking show he hosted?

BM25：`Nate favorite dish cooking show hosted`

向量：Nate's favorite dish from the cooking show he hosted.

## C004

What is the toughest part of car restoration according to Dave?

BM25：`Dave car restoration toughest difficult challenging`

向量：The part of restoring cars that Dave considers the toughest.

## C005

What did Audrey do with her pups over the weekend before 4th October, 2023?

BM25：`Audrey pups dogs weekend October 2023`

向量：What Audrey did with her pups over the weekend before October 4, 2023.

## C006

Why did Deborah spend time in the garden?

BM25：`Deborah garden gardening reason`

向量：Why Deborah spent time in the garden.

## C007

What event did Calvin attend in Boston?

BM25：`Calvin Boston event attended`

向量：The event Calvin attended in Boston.

## C008

Where did Jolene and her partner travel for a few weeks in September 2023?

BM25：`Jolene partner travel trip September 2023`

向量：Where Jolene and her partner traveled for a few weeks in September 2023.

## C009

What was Melanie's favorite book from her childhood?

BM25：`Melanie childhood favorite book`

向量：Melanie's favorite book when she was a child.

## C010

When did Melanie sign up for a pottery class?

BM25：`Melanie pottery class signed signup`

向量：When Melanie signed up for a pottery class.

## C011

When did John get married at a greenhouse?

BM25：`John married wedding greenhouse`

向量：When John got married at a greenhouse.

## C012

What did Joanna find in old notebooks last week that prompted her to reflect on her progress as a writer?

BM25：`Joanna old notebooks writing progress found`

向量：What Joanna found in old notebooks last week that made her reflect on her progress as a writer.

## C013

In what country did Jolene buy snake Seraphim?

BM25：`Jolene Seraphim snake bought country`

向量：The country where Jolene bought her snake Seraphim.

## C014

What is Nate's favorite book series about?

BM25：`Nate favorite book series story`

向量：The subject or story of Nate's favorite book series.

## C015

Does Evan live close to a beach or mountains?

BM25：`Evan live lives beach mountains nearby`

向量：Whether Evan lives near a beach or near mountains.

## C016

What does Joanna recommend to make a living room comfy like hers?

BM25：`Joanna living room comfy comfortable recommend`

向量：Joanna's recommendations for making a living room comfortable like hers.

## C017

When did John start playing professionally?

BM25：`John playing professionally professional started career`

向量：When John started playing professionally.

## C018

Which popular music composer's tunes does Tim enjoy playing on the piano?

BM25：`Tim piano composer tunes music`

向量：The popular music composer whose tunes Tim enjoys playing on the piano.

## C019

What aspect of "The Witcher 3" does John find immersive?

BM25：`John Witcher 3 immersive immersion`

向量：What John finds immersive about The Witcher 3.

## C020

Why did John's teammates sign the basketball they gave him?

BM25：`John teammates signed basketball gift`

向量：Why John's teammates signed the basketball they gave him.

## C021

How many hikes has Joanna been on?

BM25：`Joanna hike hikes hiking went`

向量：The hiking outings Joanna has been on, to determine how many hikes she mentioned.

## C022

Why does Nate like turtles as pets?

BM25：`Nate turtles pets like`

向量：Why Nate likes having turtles as pets.

## C023

What was one of Jolene's favorite games to play with her mom on the nintendo wii game system?

BM25：`Jolene mom Nintendo Wii favorite game`

向量：One of Jolene's favorite Nintendo Wii games to play with her mom.

## C024

What were Deborah's mother's hobbies?

BM25：`Deborah mother mom hobbies interests`

向量：The hobbies Deborah's mother enjoyed.

## C025

What did Melanie do after the road trip to relax?

BM25：`Melanie road trip relax relaxed afterwards`

向量：What Melanie did to relax after the road trip.

## C026

Does Deborah live close to the beach or the mountains?

BM25：`Deborah live lives beach mountains nearby`

向量：Whether Deborah lives near the beach or near the mountains.

## C027

What instruments does Melanie play?

BM25：`Melanie instrument instruments play playing`

向量：The musical instruments Melanie plays.

## C028

How many dogs does Andrew have?

BM25：`Andrew dogs dog pets number`

向量：How many dogs Andrew has.

## C029

Why didn't John want to go to Starbucks?

BM25：`John Starbucks refused wanted`

向量：Why John did not want to go to Starbucks.

## C030

What did John say about NYC, enticing Tim to visit?

BM25：`John NYC New York Tim visit`

向量：What John said about New York City that made Tim want to visit.

## C031

What kind of activities did Maria do at the picnic with her church friends?

BM25：`Maria picnic church friends activities`

向量：The activities Maria did at the picnic with her church friends.

## C032

What did Joanna recently watch and recommend to Nate on February 7, 2022?

BM25：`Joanna Nate watched recommend February 7 2022`

向量：What Joanna recently watched and recommended to Nate on February 7, 2022.

## C033

What kind of impact does Dave's blog on car mods have on people?

BM25：`Dave car mods blog people impact`

向量：How Dave's blog about car modifications affects other people.

## C034

When did Dave take a photo of a Boston clock tower?

BM25：`Dave Boston clock tower photo`

向量：When Dave took a photograph of a clock tower in Boston.

## C035

What states has Maria vacationed at?

BM25：`Maria vacation vacationed trip travel traveled`

向量：The states Maria visited on vacations or leisure trips.

## C036

When did Deborah`s mother pass away?

BM25：`Deborah mother mom died passed`

向量：When Deborah's mother passed away.

## C037

What health scares did Sam and Evan experience?

BM25：`Sam Evan health scare scares`

向量：The health scares experienced by Sam and by Evan.

## C038

When did Caroline meet up with her friends, family, and mentors?

BM25：`Caroline friends family mentors met meetup`

向量：When Caroline met up with her friends, family and mentors.

## C039

What type of cars does Dave work on at his shop?

BM25：`Dave shop cars type work`

向量：The types of cars Dave works on at his shop.

## C040

What places has Nate met new people?

BM25：`Nate met meet people places`

向量：The places where Nate has met new people.

## C041

What is Joanna's project called in the writers group?

BM25：`Joanna project writers group called name`

向量：The name of Joanna's project in the writers group.

## C042

What new activity has Tim started learning in August 2023?

BM25：`Tim learning started activity August 2023`

向量：The new activity Tim started learning in August 2023.

## C043

What games does Jolene recommend for Deborah?

BM25：`Jolene Deborah games recommend recommended`

向量：The games Jolene recommended to Deborah.

## C044

What did Evan share with Sam after their hiking trip?

BM25：`Evan Sam hiking trip shared`

向量：What Evan shared with Sam after their hiking trip.

## C045

Whose phone number did James receive during the beach outing?

BM25：`James phone number beach outing`

向量：Whose phone number James received during the beach outing.

## C046

What game is Nate currently playing and recommends to others on November 7, 2022?

BM25：`Nate game playing recommends November 7 2022`

向量：The game Nate was playing and recommending to others on November 7, 2022.

## C047

What does Nate feel he could do when out in cool places like Whispering Falls?

BM25：`Nate Whispering Falls cool places feel`

向量：What Nate feels he could do while out in cool places such as Whispering Falls.

## C048

What breed is Daisy, one of James' dogs?

BM25：`James Daisy dog breed`

向量：The breed of James' dog Daisy.

## C049

What album does Deborah recommend for meditation and deep relaxation?

BM25：`Deborah album meditation relaxation recommend`

向量：The album Deborah recommends for meditation and deep relaxation.

## C050

What did Calvin and his friends arrange for in the park?

BM25：`Calvin friends arranged park event`

向量：What Calvin and his friends arranged in the park.

## C051

What type of volunteering have John and Maria both done?

BM25：`John Maria volunteer volunteering volunteered`

向量：The types of volunteering that John and Maria have both done.

## C052

How does John feel while surfing?

BM25：`John surfing surf feel`

向量：How John feels when he is surfing.

## C053

How long was the car modification workshop in San Francisco?

BM25：`car modification workshop San Francisco duration long`

向量：The duration of the car modification workshop in San Francisco.

## C054

What did Audrey and her friends stumble across during a hike a few years back, as mentioned on June 26, 2023?

BM25：`Audrey friends hiking stumbled found June 26 2023`

向量：What Audrey and her friends stumbled across on a hike a few years earlier, as recalled on June 26, 2023.

## C055

When did Maria join a gym?

BM25：`Maria gym joined join`

向量：When Maria joined a gym.

## C056

What is Evan's favorite food?

BM25：`Evan favorite food dish`

向量：Evan's favorite food.

## C057

What is Dave's way to share his passion with others?

BM25：`Dave passion share sharing others`

向量：How Dave shares his passion with other people.

## C058

When did Melanie go to the pottery workshop?

BM25：`Melanie pottery workshop attended went`

向量：When Melanie went to the pottery workshop.

## C059

When is Melanie planning on going camping?

BM25：`Melanie camping planning planned trip`

向量：When Melanie plans to go camping.

## C060

What did Evan mention he had been searching for fruitlessly for half an hour?

BM25：`Evan searching searched half hour`

向量：What Evan said he had been searching for unsuccessfully for half an hour.

## C061

What event did John participate in to show support for veterans' rights?

BM25：`John veterans rights event support`

向量：The event John participated in to support veterans' rights.

## C062

What does John believe is important for children regarding veterans?

BM25：`John children veterans important`

向量：What John believes children should understand or do regarding veterans.

## C063

What are the names of Jolene's snakes?

BM25：`Jolene snakes snake names named`

向量：The names of Jolene's snakes.

## C064

Why did Maria sit with the little girl at the shelter event in February 2023?

BM25：`Maria girl shelter event February 2023`

向量：Why Maria sat with the little girl at the shelter event in February 2023.

## C065

What motivates Joanna to keep writing even on tough days?

BM25：`Joanna writing tough days motivation`

向量：What motivates Joanna to keep writing on difficult days.

## C066

How long has Melanie been practicing art?

BM25：`Melanie art practicing started years`

向量：How long Melanie has been practicing art.

## C067

When did Melanie go on a hike after the roadtrip?

BM25：`Melanie hike hiking roadtrip road trip after`

向量：When Melanie went on a hike after the road trip.

## C068

How does John describe the camping trip with Max?

BM25：`John camping trip Max describe`

向量：How John describes his camping trip with Max.

## C069

When did Melanie go to the museum?

BM25：`Melanie museum visited went`

向量：When Melanie went to the museum.

## C070

What aspects of the Harry Potter universe will be discussed in John's fan project collaborations?

BM25：`John Harry Potter fan project collaborations`

向量：The parts of the Harry Potter universe that John plans to discuss in his fan project collaborations.

## C071

What kind of dream did James have recently?

BM25：`James dream dreamed recently`

向量：The kind of dream James recently had.

## C072

What did Melanie and her family see during their camping trip last year?

BM25：`Melanie family camping last year saw`

向量：What Melanie and her family saw on their camping trip last year.

## C073

What would be a good hobby related to his travel dreams for Tim to pick up?

BM25：`Tim travel dreams hobby interests`

向量：Tim's travel dreams and interests that could suggest a related hobby for him to take up.

## C074

Where did Deborah get her cats?

BM25：`Deborah cats adopted got`

向量：Where Deborah got her cats.

## C075

Do Jon and Gina start businesses out of what they love?

BM25：`Jon Gina business businesses passion love`

向量：Whether Jon and Gina started businesses based on things they love.

## C076

What did Evan recommend Sam acquire to get started with painting?

BM25：`Evan Sam painting started recommended supplies`

向量：What Evan recommended Sam acquire to begin painting.

## C077

What offer does Gina make to Jon regarding social media?

BM25：`Gina Jon social media offer help`

向量：Gina's offer to Jon concerning social media.

## C078

How many times has Joanna found new hiking trails?

BM25：`Joanna hiking trails found discovered`

向量：The occasions when Joanna found new hiking trails, to count how many times she did so.

## C079

What did Jolene design inspired by their love for space and engines?

BM25：`Jolene design designed space engines`

向量：What Jolene designed based on a love of space and engines.

## C080

What kind of experiences are Audrey's dogs the best companions for?

BM25：`Audrey dogs companions experiences`

向量：The kinds of experiences Audrey's dogs are especially good companions for.

## C081

What does Dave aim to do with his passion for cars?

BM25：`Dave cars passion aim goals`

向量：What Dave aims to achieve through his passion for cars.

## C082

What type of show did Nate host where he taught vegan ice cream recipes?

BM25：`Nate show hosted vegan ice cream recipes`

向量：The type of show Nate hosted to teach vegan ice cream recipes.

## C083

Does Dave's shop employ a lot of people?

BM25：`Dave shop employ employees staff people`

向量：The number or size of the staff employed at Dave's shop.

## C084

What project was Jolene working on as of 1 February, 2023?

BM25：`Jolene project working February 1 2023`

向量：The project Jolene was working on as of February 1, 2023.

## C085

What book did John recently finish rereading that left him feeling inspired and hopeful about following dreams?

BM25：`John book rereading inspired hopeful dreams`

向量：The book John recently finished rereading that inspired him to pursue his dreams.

## C086

What was Tim's huge writing issue last week,as mentioned on November 6, 2023?

BM25：`Tim writing issue problem November 6 2023`

向量：The major writing issue Tim had the previous week, as mentioned on November 6, 2023.

## C087

What did John suggest James practice before playing FIFA 23 together?

BM25：`John James FIFA 23 practice suggested`

向量：What John suggested James practice before they played FIFA 23 together.

## C088

Why did Jolene have to reschedule their meeting with Deborah on September 8, 2023?

BM25：`Jolene Deborah meeting reschedule September 8 2023`

向量：The reason Jolene had to reschedule the meeting with Deborah on September 8, 2023.

## C089

What has John been able to help the younger players achieve?

BM25：`John younger players help achieve`

向量：What John has helped the younger players achieve.

## C090

What did Evan start doing a few years back as a stress-buster?

BM25：`Evan stress buster started years`

向量：The activity Evan started a few years ago to relieve stress.

## C091

When did Deborah lead a meditation session during the sunset?

BM25：`Deborah meditation session sunset led`

向量：When Deborah led a meditation session at sunset.

## C092

Which year did Jolene and her partner start dating?

BM25：`Jolene partner dating started relationship year`

向量：The year Jolene and her partner began dating.

## C093

When did Gina team up with a local artist for some cool designs?

BM25：`Gina local artist designs collaboration`

向量：When Gina teamed up with a local artist to create designs.

## C094

Where was Tim in the week before 16 November 2023?

BM25：`Tim visited traveled week November 16 2023`

向量：Where Tim was during the week before November 16, 2023.

## C095

What personal health incidents does Evan face in 2023?

BM25：`Evan personal health incidents 2023`

向量：The personal health incidents Evan experienced in 2023.

## C096

When did Maria receive a medal from the homeless shelter?

BM25：`Maria medal homeless shelter received`

向量：When Maria received a medal from the homeless shelter.

## C097

What activities has Melanie done with her family?

BM25：`Melanie family activities together`

向量：The activities Melanie has done with her family.

## C098

How did John overcome his ankle injury from last season?

BM25：`John ankle injury last season recovery recovered`

向量：How John recovered from his ankle injury last season.

## C099

What kind of water does Evan suggest Sam try as an alternative to soda?

BM25：`Evan Sam soda alternative water`

向量：The type of water Evan suggested Sam try instead of soda.

## C100

Where did Dave come back from with insights on car modification on 1st September 2023?

BM25：`Dave returned car modification insights September 1 2023`

向量：The place Dave returned from with new insights about car modification, as mentioned on September 1, 2023.

## C101

When Gina has lost her job at Door Dash?

BM25：`Gina Door Dash DoorDash job lost`

向量：When Gina lost her job at Door Dash.

## C102

What type of car did Evan get after his old Prius broke down?

BM25：`Evan Prius broke car bought replacement`

向量：The type of car Evan got after his old Prius broke down.

## C103

Which events has Jon participated in to promote his business venture?

BM25：`Jon business venture events participated promote`

向量：The events Jon participated in to promote his business venture.

## C104

When did someone write Joanna a touching letter?

BM25：`Joanna touching letter received written`

向量：When someone wrote a touching letter to Joanna.

## C105

Which places or events have John and James planned to meet at?

BM25：`John James planned meet meeting places events`

向量：The places or events where John and James planned to meet.

## C106

What type of jewelry does Audrey make?

BM25：`Audrey jewelry jewellery makes`

向量：The type of jewelry Audrey makes.

## C107

Which outdoor gear company likely signed up John for an endorsement deal?

BM25：`John outdoor gear company endorsement signed`

向量：The outdoor gear company that likely signed John for an endorsement deal.

## C108

What kind of modifications has Dave been working on in the car mod workshop?

BM25：`Dave car mod modification workshop working`

向量：The modifications Dave has been working on in the car modification workshop.

## C109

What did John and his friends do with the remaining money after helping the dog shelter?

BM25：`John friends money remaining dog shelter`

向量：What John and his friends did with the money left after helping the dog shelter.

## C110

What kind of meal did John and his family make together in the photo shared by John?

BM25：`John family meal made cooking photo`

向量：The meal John and his family made together in the photo he shared.

## C111

When did Nate get Tilly for Joanna?

BM25：`Nate Joanna Tilly got acquired`

向量：When Nate got Tilly for Joanna.

## C112

Did Jolene teach herself how to play the console?

BM25：`Jolene console play taught herself learning`

向量：Whether Jolene taught herself how to play the console.

## C113

What activity did Jolene and her partner plan to do together instead of resuming yoga?

BM25：`Jolene partner yoga instead activity planned`

向量：The activity Jolene and her partner planned to do together instead of resuming yoga.

## C114

When did Caroline have a picnic?

BM25：`Caroline picnic went date`

向量：When Caroline had a picnic.

## C115

What did Anthony and John end up playing during the charity event?

BM25：`Anthony John charity event played`

向量：What Anthony and John ended up playing at the charity event.

## C116

When did James, Samantha and John go to the baseball game together?

BM25：`James Samantha John baseball game`

向量：When James, Samantha and John went to the baseball game together.

## C117

When did Calvin met with local artists in Boston?

BM25：`Calvin local artists Boston met`

向量：When Calvin met with local artists in Boston.

## C118

Which torunament did Nate win in the beginning of November 2022?

BM25：`Nate tournament won November 2022`

向量：The tournament Nate won at the beginning of November 2022.

## C119

Which US state was Sam travelling in during October 2023?

BM25：`Sam traveling travelling trip October 2023 state`

向量：The US state Sam traveled in during October 2023.

## C120

What is something that Audrey often dresses up her dogs with?

BM25：`Audrey dogs dressed dresses accessories`

向量：What Audrey often dresses her dogs with.

## C121

What kind of books does Caroline have in her library?

BM25：`Caroline library books kinds`

向量：The types of books in Caroline's library.

## C122

How many people attended the gaming party hosted by Nate in June 2022?

BM25：`Nate gaming party June 2022 people attended`

向量：The number of people at the gaming party Nate hosted in June 2022.

## C123

How did Evan feel when he painted the piece with the bird flying over it?

BM25：`Evan painted painting bird flying felt`

向量：How Evan felt when he painted the piece with a bird flying over it.

## C124

What subject have Caroline and Melanie both painted?

BM25：`Caroline Melanie painted painting subject`

向量：The subject that both Caroline and Melanie have painted.

## C125

What inspired James to create his game?

BM25：`James game created inspiration inspired`

向量：What inspired James to create his game.

## C126

What new content is Nate creating for YouTube?

BM25：`Nate YouTube new content creating`

向量：The new content Nate is creating for YouTube.

## C127

What kind of stress was Sam dealing with in October 2023?

BM25：`Sam stress October 2023 dealing`

向量：The kind of stress Sam was dealing with in October 2023.

## C128

What inspires Joanna to create drawings of her characters?

BM25：`Joanna characters drawings inspiration inspired`

向量：What inspires Joanna to draw her characters.

## C129

Is Deborah married?

BM25：`Deborah married marriage spouse wedding`

向量：Whether Deborah is married.

## C130

What martial arts has John done?

BM25：`John martial arts trained practice`

向量：The martial arts John has practiced.

## C131

What kind of event did John and his family attend in June 2023?

BM25：`John family event June 2023 attended`

向量：The kind of event John and his family attended in June 2023.

## C132

What inspired Joanna's new screenplay on 25 February, 2022?

BM25：`Joanna screenplay inspired February 25 2022`

向量：The inspiration for Joanna's new screenplay on February 25, 2022.

## C133

What is Jolene's favorite book which she mentioned on 4 February, 2023?

BM25：`Jolene favorite book February 4 2023`

向量：Jolene's favorite book mentioned on February 4, 2023.

## C134

What natural disaster affected John's old area on 7 July, 2023?

BM25：`John old area natural disaster July 7 2023`

向量：The natural disaster that affected John's former area on July 7, 2023.

## C135

Where did Jolene and her partner spend most of September 2023?

BM25：`Jolene partner September 2023 spent traveled`

向量：Where Jolene and her partner spent most of September 2023.

## C136

When did Gina get her tattoo?

BM25：`Gina tattoo got date`

向量：When Gina got her tattoo.

## C137

How many children does Melanie have?

BM25：`Melanie children kids family number`

向量：How many children Melanie has.

## C138

How many games has John mentioned winning?

BM25：`John games wins won winning`

向量：The games John has mentioned winning, to count the wins.

## C139

What does Dave do when he feels his creativity is frozen?

BM25：`Dave creativity frozen blocked feels`

向量：What Dave does when he feels creatively blocked.

## C140

What J.K. Rowling quote does Tim resonate with?

BM25：`Tim JK Rowling quote resonate`

向量：The J.K. Rowling quote Tim identifies with.

## C141

Which activity has John done apart from yoga at the studio?

BM25：`John studio yoga activity classes`

向量：The activity John has done at the studio besides yoga.

## C142

Which hobby did Dave pick up in October 2023?

BM25：`Dave hobby started October 2023`

向量：The hobby Dave took up in October 2023.

## C143

When did Calvin first travel to Tokyo?

BM25：`Calvin Tokyo first trip travel`

向量：When Calvin traveled to Tokyo for the first time.

## C144

What did Caroline see at the council meeting for adoption?

BM25：`Caroline adoption council meeting saw`

向量：What Caroline saw at the council meeting for adoption.

## C145

How did the audience in Tokyo react when Calvin sang one of his songs?

BM25：`Calvin Tokyo audience song sang reaction`

向量：How the audience in Tokyo reacted when Calvin sang one of his songs.

## C146

What is Jon offering to the dancers at his dance studio?

BM25：`Jon dancers dance studio offering`

向量：What Jon is offering to the dancers at his studio.

## C147

How is Maria's new puppy adjusting to its new home?

BM25：`Maria puppy home adjusting`

向量：How Maria's new puppy is adjusting to its new home.

## C148

What was Johns's reaction to sealing the deal with the beverage company?

BM25：`John beverage company deal reaction`

向量：John's reaction to sealing the deal with the beverage company.

## C149

What kind of art does Caroline make?

BM25：`Caroline art makes creates`

向量：The kind of art Caroline makes.

## C150

What type of mobile application does James plan to build with John?

BM25：`James John mobile application app build`

向量：The type of mobile application James plans to build with John.

## C151

What time management techniques do Deborah and Jolene use?

BM25：`Deborah Jolene time management techniques`

向量：The techniques Deborah and Jolene use to manage their time.

## C152

What ingredient did Nate use to make the ice cream lactose-free?

BM25：`Nate ice cream lactose free ingredient`

向量：The ingredient Nate used to make his ice cream lactose-free.

## C153

What did John receive for achieving second place in the tournament?

BM25：`John tournament second place received prize`

向量：What John received for placing second in the tournament.

## C154

When did Calvin first get interested in cars?

BM25：`Calvin cars interest interested first`

向量：When Calvin first became interested in cars.

## C155

When did Joanna have an audition for a writing gig?

BM25：`Joanna writing gig audition`

向量：When Joanna auditioned for a writing gig.

## C156

When did Andrew and his girlfriend go fishing?

BM25：`Andrew girlfriend fishing went`

向量：When Andrew and his girlfriend went fishing.

## C157

Where has Maria made friends?

BM25：`Maria friends made met friendship`

向量：The places where Maria has made friends.

## C158

Who supports Calvin in tough times?

BM25：`Calvin tough times support`

向量：Who supports Calvin during difficult times.

## C159

How long did the trail hike that Audrey went on with her pups take?

BM25：`Audrey pups trail hike duration hours`

向量：The time taken by Audrey's trail hike with her pups.

## C160

What decision did James and Samantha make on 31 October, 2022?

BM25：`James Samantha decision October 31 2022`

向量：The decision James and Samantha made on October 31, 2022.

## C161

Who gave Maria's family money when she was younger and her family was going through tough times?

BM25：`Maria family money younger tough times help`

向量：Who gave Maria's family money when she was younger and her family was struggling financially.

## C162

Who performed at the concert at Melanie's daughter's birthday?

BM25：`Melanie daughter birthday concert performed`

向量：Who performed at the concert for Melanie's daughter's birthday.

## C163

When did Nate get purple hair?

BM25：`Nate purple hair got`

向量：When Nate got purple hair.

## C164

What genre is Joanna's first screenplay?

BM25：`Joanna first screenplay genre`

向量：The genre of Joanna's first screenplay.

## C165

Which book did Tim recommend to John as a good story on 8th December, 2023?

BM25：`Tim John book recommended December 8 2023`

向量：The book Tim recommended to John as a good story on December 8, 2023.

## C166

How does Dave feel about the reactions of people when they see the finished restoration project?

BM25：`Dave restoration finished project people reactions feel`

向量：How Dave feels about people's reactions when they see a finished restoration project.

## C167

What type of projects is Jolene interested in getting involved in the future?

BM25：`Jolene projects interested future`

向量：The types of projects Jolene is interested in joining in the future.

## C168

How does John describe the game season for his team?

BM25：`John team game season describe`

向量：How John describes his team's game season.

## C169

What painting did Evan share with Sam in October?

BM25：`Evan Sam painting shared October`

向量：The painting Evan shared with Sam in October.

## C170

How many turtles does Nate have?

BM25：`Nate turtles turtle number pets`

向量：How many turtles Nate has.

## C171

What did Joanna take a picture of near Fort Wayne last summer?

BM25：`Joanna picture photographed Fort Wayne summer`

向量：What Joanna photographed near Fort Wayne last summer.

## C172

How many days did James plan to spend on his trip in Canada?

BM25：`James Canada trip planned days duration`

向量：The number of days James planned to spend on his trip to Canada.

## C173

What workshop did Caroline attend recently?

BM25：`Caroline workshop attended recently`

向量：The workshop Caroline attended recently.

## C174

What plans do Calvin and Dave have for when Calvin visits Boston?

BM25：`Calvin Dave Boston visit plans`

向量：The plans Calvin and Dave have for Calvin's visit to Boston.

## C175

When did Caroline go to the LGBTQ conference?

BM25：`Caroline LGBTQ conference attended`

向量：When Caroline went to the LGBTQ conference.

## C176

What do Melanie's family give her?

BM25：`Melanie family give given`

向量：What Melanie's family give her.

## C177

What book recommendations has Joanna given to Nate?

BM25：`Joanna Nate book books recommendations`

向量：The books Joanna has recommended to Nate.

## C178

What organization does Audrey donate a portion of his profits to?

BM25：`Audrey profits donate organization charity`

向量：The organization Audrey donates part of his profits to.

## C179

Which TV series does Tim mention watching?

BM25：`Tim TV television series watching`

向量：The TV series Tim has mentioned watching.

## C180

What recurring issue frustrates Sam at the grocery store?

BM25：`Sam grocery store recurring problem frustrated`

向量：The recurring problem that frustrates Sam at the grocery store.

## C181

Which ailment does Sam have to face due to his weight?

BM25：`Sam weight ailment health condition`

向量：The ailment Sam faces because of his weight.

## C182

What are Melanie's pets' names?

BM25：`Melanie pets names named`

向量：The names of Melanie's pets.

## C183

How many times has John injured his ankle?

BM25：`John ankle injured injury times`

向量：John's ankle injuries, to count how many times he has injured it.

## C184

When did Deborah meet Anna?

BM25：`Deborah Anna met meeting`

向量：When Deborah met Anna.

## C185

What did the posters at the poetry reading say?

BM25：`poetry reading posters words text`

向量：What was written on the posters at the poetry reading.

## C186

Does James live in Connecticut?

BM25：`James live lives Connecticut`

向量：Whether James lives in Connecticut.

## C187

What animal do both Nate and Joanna like?

BM25：`Nate Joanna animal animals like`

向量：The animal that Nate and Joanna both like.

## C188

Would John be open to moving to another country?

BM25：`John moving country abroad open`

向量：Whether John would be willing to move to another country.

## C189

What is the type of game "Xenoblade Chronicles" that Nate is playing?

BM25：`Nate Xenoblade Chronicles game type genre`

向量：The type or genre of Xenoblade Chronicles, the game Nate is playing.

## C190

What does Tim have that serves as a reminder of hard work and is his prized possession?

BM25：`Tim prized possession hard work reminder`

向量：Tim's prized possession that reminds him of hard work.

## C191

How many of Joanna's writing have made it to the big screen?

BM25：`Joanna writing writings big screen adapted`

向量：How many of Joanna's writings have been adapted for the big screen.

## C192

How long has John been playing the drums as of 27 March, 2022?

BM25：`John drums playing years March 27 2022`

向量：How long John had been playing the drums as of March 27, 2022.

## C193

What instrument is Tim learning to play in December 2023?

BM25：`Tim instrument learning play December 2023`

向量：The instrument Tim was learning to play in December 2023.

## C194

When did Calvin plan on travelling to Tokyo the second time?

BM25：`Calvin Tokyo second trip plan travel`

向量：When Calvin planned to travel to Tokyo for the second time.

## C195

When did James ask Samantha to be his girlfriend?

BM25：`James Samantha girlfriend asked dating`

向量：When James asked Samantha to be his girlfriend.

## C196

Which country were Jolene and her mother visiting in 2010?

BM25：`Jolene mother visiting country 2010`

向量：The country Jolene and her mother were visiting in 2010.

## C197

What advice did James receive from the famous players he met at the tournament?

BM25：`James famous players tournament advice`

向量：The advice James received from the famous players he met at the tournament.

## C198

What book recommendation did Tim give to John for the trip?

BM25：`Tim John book recommendation trip`

向量：The book Tim recommended to John for the trip.

## C199

What positive change did Jolene experience during the retreat?

BM25：`Jolene retreat positive change experienced`

向量：The positive change Jolene experienced during the retreat.

## C200

What organization is John teaming up with for his charity work?

BM25：`John charity organization teaming work`

向量：The organization John is teaming up with for charity work.

