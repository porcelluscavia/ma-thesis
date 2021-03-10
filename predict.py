# coding: utf-8

# called by kfold.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import model_selection, svm
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from ngram_lime.lime.lime_text import LimeTextExplainer
import re
import sys
import argparse
import pickle
import datetime
from transformers import FlaubertModel, FlaubertTokenizer
import torch


def split_ngrams(joined_ngrams):
    # Used by the TfidfVectorizer, important for the modified LIME
    return joined_ngrams.split(' ')


def encode(ngrams_train, ngrams_test, labels_train, labels_test,
           max_features=5000):

    label_encoder = LabelEncoder()
    train_y = label_encoder.fit_transform(labels_train)
    test_y = label_encoder.transform(labels_test)

    vectorizer = TfidfVectorizer(max_features=max_features,
                                 analyzer=split_ngrams)
    train_x = vectorizer.fit_transform(ngrams_train)
    test_x = vectorizer.transform(ngrams_test)

    return train_x, test_x, train_y, test_y, label_encoder, vectorizer


def encode_embeddings(toks_train, toks_test, labels_train, labels_test,
                      flaubert_tokenizer, flaubert, max_len=42):
    token_ids_train = [flaubert_tokenizer.encode(toks, max_length=max_len,
                                                 truncation=True,
                                                 padding='max_length')
                       for x in toks_train]
    train_x = flaubert(torch.tensor(token_ids_train))[0]

    token_ids_test = [flaubert_tokenizer.encode(toks, max_length=max_len,
                                                truncation=True,
                                                padding='max_length')
                       for x in toks_test]
    test_x = flaubert(torch.tensor(token_ids_test))[0]

    label_encoder = LabelEncoder()
    train_y = label_encoder.fit_transform(labels_train)
    test_y = label_encoder.transform(labels_test)

    return train_x, test_x, train_y, test_y, label_encoder, max_len


def preprocess_and_vectorize(utterance, vectorizer):
    return vectorizer.transform([utterance])
    # return vectorizer.transform([preprocess(utterance)])


def train(train_x, train_y, linear_svc, class_weight=None):
    if linear_svc:
        model = svm.LinearSVC(C=1.0, class_weight=class_weight)
    else:
        # Binary cases
        model = svm.SVC(C=1.0, probability=True, class_weight=class_weight)
    model.fit(train_x, train_y)
    return model


def predict(model, test_x):
    return model.predict(test_x)


def predict_instance(model, utterance, label_encoder, vectorizer, linear_svc):
    # x = vectorizer.transform([preprocess(utterance)])
    x = vectorizer.transform([utterance])
    pred = model.predict(x)
    margins = model.decision_function(x)
    if linear_svc:
        exp = np.exp(margins)
        softmax = exp / np.sum(exp)
    #     print("{}: {}".format(utterance, softmax.round(3)))
        return pred[0], label_encoder.inverse_transform(pred)[0], margins, softmax
    return pred[0], label_encoder.inverse_transform(pred)[0], margins, model.predict_proba(x)


def predict_proba2(model, data, vectorizer, linear_svc, n_labels=4):
    probs = np.zeros((len(data), n_labels))
    for i, utterance in enumerate(data):
        x = vectorizer.transform([utterance])
        if linear_svc:
            pred = model.predict(x)
            margins = model.decision_function(x)
            exp = np.exp(margins)
            probs[i] = exp / np.sum(exp)  # softmax
        else:
            probs[i] = model.predict_proba(x)
    GET_NGRAMS = True
    return probs


def predict_proba_embeddings(model, data, flaubert, flaubert_tokenizer,
                             linear_svc, max_len, n_labels=2):
    probs = np.zeros((len(data), n_labels))
    for i, utterance in enumerate(data):
        token_ids = [flaubert_tokenizer.encode(utterance, max_length=max_len,
                                               truncation=True,
                                               padding='max_length')]
        x = flaubert(torch.tensor(token_ids))[0]
        if linear_svc:
            pred = model.predict(x)
            margins = model.decision_function(x)
            exp = np.exp(margins)
            probs[i] = exp / np.sum(exp)  # softmax
        else:
            probs[i] = model.predict_proba(x)
    GET_NGRAMS = True
    return probs


def score(pred, test_y):
    return accuracy_score(test_y, pred), f1_score(test_y, pred, average='macro'), confusion_matrix(test_y, pred)


def support_vectors(model, label_encoder, train_x, train_x_raw,
                    labels=[0, 1, 2, 3]):
    for label in labels:
        print(label_encoder.inverse_transform([label])[0])
        print('==========================\n')
        dec_fn = model.decision_function(train_x)[:, label]
        # support vectors and vectors 'in the middle of the street'
        support_vector_indices_pos = np.where(np.logical_and(dec_fn > 0, dec_fn <= 1))[0]
        print('positive side')
        for idx in support_vector_indices_pos:
            print('-', train_x_raw[idx])
        support_vector_indices_neg = np.where(np.logical_and(dec_fn <= 0, dec_fn >= -1))[0]
        print()
        print('negative side')
        for idx in support_vector_indices_pos:
            print('-', train_x_raw[idx])
        print('\n\n')


def instances_far_from_decision_boundary(model, label_encoder, train_x,
                                         train_x_raw, labels=[0, 1, 2, 3]):
    for label in labels:
        print(label_encoder.inverse_transform([label])[0])
        print('==========================\n')
        dec_fn = model.decision_function(train_x)[:, label]
        # vectors far away from the decision boundary
        support_vector_indices_pos = np.where(dec_fn > 3)[0]
        print('positive side')
        for idx in support_vector_indices_pos:
            print(dec_fn[idx].round(3), train_x_raw[idx])
    #     support_vector_indices_neg = np.where(dec_fn < -3)[0]
    #     print()
    #     print('negative side')
    #     for idx in support_vector_indices_pos:
    #         print('-', train_x_raw[idx])
        print('\n\n')


def explain_lime(classifier, vectorizer, label_encoder, n_labels, test_x_raw,
                 test_x_ngrams, test_x, test_y, out_folder, linear_svc,
                 flaubert=None, flaubert_tokenizer=None, max_len=None):
    labels = list(range(n_labels))
    explainer = LimeTextExplainer(class_names=label_encoder.inverse_transform(labels),
                                  split_expression=split_ngrams,
                                  bow=True, ngram_lvl=True,
                                  utterance2ngrams=split_ngrams,
                                  recalculate_ngrams=False)
    if flaubert:
        predict_function = lambda z: predict_proba_embeddings(model, z,
                                                              flaubert,
                                                              flaubert_tokenizer,
                                                              linear_svc,
                                                              max_len, n_labels)
    else:
        predict_function = lambda z: predict_proba2(classifier, z, vectorizer,
                                                    linear_svc, n_labels)
    with open(out_folder + 'predictions.tsv', 'w+', encoding='utf8') as f_pred:
        for idx, (utterance, ngrams, encoded, y) in enumerate(zip(test_x_raw,
                                                                  test_x_ngrams,
                                                                  test_x,
                                                                  test_y)):
            y_raw = label_encoder.inverse_transform([y])[0]
            pred_enc = classifier.predict(encoded)[0]
            pred_raw = label_encoder.inverse_transform([pred_enc])[0]
            f_pred.write('{}\t{}\t{}\t{}\n'.format(idx, utterance,
                                                   y_raw, pred_raw))

            exp = explainer.explain_instance(ngrams,
                                             predict_function,
                                             num_features=20,
                                             labels=labels,
                                             # labels=interesting_labels
                                             num_samples=1000
                                             )
            for lab in labels:
                lime_results = exp.as_list(label=lab)
                lab_raw = label_encoder.inverse_transform([lab])[0]
                with open('{}/importance_values_{}.txt'.format(out_folder,
                                                               lab_raw),
                          'a+', encoding='utf8') as f:
                    for feature, score in lime_results:
                        f.write('{}\t{}\t{:.10f}\n'.format(idx, feature, score))

            if idx % 50 == 0:
                now = datetime.datetime.now()
                print(idx)
                print(now)
                print('"' + utterance + '""')
                print('ACTUAL', y_raw)
                print('PREDICTED', pred_raw)
                print('\n')
                with open(out_folder + '/log.txt', 'a', encoding='utf8') as f:
                    f.write(str(idx) + '  --  ' + str(now) + '  --  "' + utterance + '""\n')
                    f.write('ACTUAL: ' + str(y_raw) + '\n')
                    f.write('PREDICTED: ' + str(pred_raw) + '\n')
                    for label_nr in range(n_labels):
                        lab = label_encoder.inverse_transform([label_nr])[0]
                        f.write('Class ' + lab + ': ' + ', '.join(
                            ['{}\t{:.5f}'.format(x[0], x[1]) for x in exp.as_list(label=label_nr)[:5]]) + '\n')
                    f.write('\n')
