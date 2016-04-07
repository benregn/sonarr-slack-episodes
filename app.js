const axios = require('axios');
const botkit = require('botkit');
const moment = require('moment');

const controller = botkit.slackbot({ debug: false });

const bot = controller.spawn({
  token: process.env.SLACK_API_KEY,
  retry: 100
});

bot.api.team.info({}, function (err, res) {
  if (err) throw err;

  controller.storage.teams.save(res.team, function (err, res) {
    if (err) throw err;

    controller.setupWebserver(process.env.PORT, function (err, server) {
      if (err) throw err;
      controller.createWebhookEndpoints(server);
    });

    controller.on('slash_command', function (bot, message) {
      const start = moment().subtract(1, 'days').format('YYYY-MM-DDThh:mm:ss');
      const end = moment().add(message.text || 0, 'days').format('YYYY-MM-DDThh:mm:ss');
      const url = `${process.env.SONARR_URL}/api/calendar?apikey=${process.env.SONARR_API_KEY}&start=${start}Z&end=${end}Z`;

      axios.get(url)
        .then(res => res.data)
        .then(data => data.reduce((prev, curr) => {
          const airDate = curr.airDate;
          const episode = {
            'episodeTitle': curr.title,
            'seriesTitle': curr.series.title,
            'episodeNumber': curr.episodeNumber,
            'seasonNumber': curr.seasonNumber
          };
          if (!prev.hasOwnProperty(airDate)) prev[airDate] = [episode];
          else prev[airDate].push(episode);
          return prev;
        }, {}))
        .then(data => Object.keys(data).map(key => {
          const day = moment(key).format('*dddd* - MM/DD');
          const ep = data[key].map(ep => (
            `${ep.seriesTitle} (S${ep.seasonNumber}E${ep.episodeNumber} - ${ep.episodeTitle})`
          )).join('\n');
          return `${day}\n${ep}`;
        }))
        .then(episodes => episodes.join('\n'))
        .then(response => bot.replyPublic(message, response))
        .catch(res => {
          console.log('err', res);
        });
    });
  });
});
