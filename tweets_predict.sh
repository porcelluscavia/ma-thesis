#!/bin/sh

# In the case of line ending problems (Windows vs. UNIX encodings), run:
# sed -i 's/\r$//' tweets.sh

# python3 get_tweets.py
# python3 tweet_cleanup.py
# python3 extract_features.py tweets models/tweets --lower
# python3 feature_correlation.py models/tweets
# python3 prepare_folds.py models/tweets 10

# for i in $(seq 0 9); do
#     echo "Setting up fold $i"
#     screen -dmS tweets$i
#     screen -S tweets$i -X stuff "python3 predict_fold.py models/tweets tweets $i --z 2000
# "
# done

# python3 extract_features.py tweets models/tweets-bpe --lower --bpe
# python3 feature_correlation.py models/tweets-bpe
# python3 prepare_folds.py models/tweets-bpe 10

# for i in $(seq 0 9); do
#     echo "Setting up fold $i"
#     screen -dmS tweets-bpe$i
#     screen -S tweets-bpe$i -X stuff "python3 predict_fold.py models/tweets-bpe tweets $i --z 2000
# "
# done

# python3 extract_features.py tweets models/tweets-uncased --lower
# python3 feature_correlation.py models/tweets-uncased
# python3 prepare_folds.py models/tweets-uncased 10

# for i in $(seq 0 9); do
#     echo "Setting up fold $i"
#     screen -dmS tweets-uncased$i
#     screen -S tweets-uncased$i -X stuff "python3 predict_fold.py models/tweets-uncased tweets $i --z 2000
# "
# done

python3 extract_features.py tweets models/tweets-cased
python3 feature_correlation.py models/tweets-cased
python3 prepare_folds.py models/tweets-cased 10

for i in $(seq 0 9); do
    echo "Setting up fold $i"
    screen -dmS tweets-cased$i
    screen -S tweets-cased$i -X stuff "python3 predict_fold.py models/tweets-cased tweets $i --z 2000
"
done

