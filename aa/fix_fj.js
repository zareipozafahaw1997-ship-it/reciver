db.settings.updateOne(
  {key: "force_join"},
  {$set: {enabled: true, channel: "@Zloginbot"}}
);
print("Done");
