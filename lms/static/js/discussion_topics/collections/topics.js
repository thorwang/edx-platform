var edx = edx || {};

(function(Backbone, topicModel) {
    'use strict';

    edx.discussions = edx.discussions || {};

    edx.discussions.DiscussionTopicsCollection = Backbone.Collection.extend({
        model : topicModel

    });
}).call(this, Backbone, edx.discussions.DiscussionTopicModel);
