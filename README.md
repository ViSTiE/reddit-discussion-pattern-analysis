# Reddit Public Discussion Pattern Research

## Overview

This project is an independent research tool designed to analyze publicly available Reddit discussions using the official Reddit Data API.

The purpose of this system is to explore recurring topic patterns and commonly expressed discussion themes across selected public subreddits.

The project is strictly exploratory and non-commercial.

---

## Research Objective

The goal of this project is to:

- Identify recurring public discussion topics
- Cluster semantically similar posts
- Evaluate engagement levels within discussion threads
- Understand general patterns in publicly available conversations

This tool does not interact with Reddit users and does not modify Reddit content in any way.

---

## Compliance & Responsible Use

This project adheres to:

- Reddit Developer Terms
- Reddit Data API Terms
- Responsible Builder Policy

Specifically:

- Only publicly available Reddit data accessed via the official API is used.
- All API requests respect Reddit rate limits.
- No scraping is performed.
- No private subreddit data is accessed.
- No user profiling is conducted.
- No cross-user behavioral aggregation is performed.
- No personal data beyond post-level metadata is stored.
- Reddit data is not used to train machine learning models.
- Data is not resold, licensed, or shared with third parties.
- The project is for personal research purposes only.

---

## Technical Summary

The system:

1. Retrieves recent public posts from selected subreddits.
2. Performs structured text analysis.
3. Generates local semantic embeddings.
4. Clusters related discussion topics.
5. Computes engagement-based metrics.

All semantic embeddings are generated locally using open-source models.

The system runs independently outside of Reddit and does not create interactive Reddit features.

---

## Scope

Currently limited to selected public subreddits such as:

- r/startups
- r/smallbusiness
- r/Entrepreneur
- r/SaaS

No attempt is made to access private or restricted communities.

---

## Non-Commercial Statement

This project is not monetized and is not used for advertising, resale, or commercial analytics purposes.

---

## Status

Active personal research project.
