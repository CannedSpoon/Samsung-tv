// Short, easy-to-type words for generated passwords (three words + two digits).
// 256 words = 8 bits each; with the digits about 30 bits, which the login
// lockout and global slowdown make impractical to guess over the network.
'use strict';
module.exports = (
  'acorn amber anchor apple apron arrow aspen atlas autumn badge bagel baker ' +
  'bamboo banjo barley basil beach beacon bean berry birch biscuit blaze bloom ' +
  'blossom bonfire branch breeze brick bridge brook bubble bucket cabin cactus ' +
  'camel candle canoe canyon carrot castle cedar cello cherry chess cider cinema ' +
  'citrus clover cobalt cocoa comet compass copper coral cotton cougar crane ' +
  'crayon creek cricket crystal cuckoo daisy delta denim desert diamond dingo ' +
  'dolphin donut dragon drum dune eagle echo ember emerald falcon feather fern ' +
  'fiddle fig finch fjord flame flint forest fossil fox galaxy garden gecko ' +
  'ginger glacier globe goose granite grape gravel guitar gull harbor hazel ' +
  'heron hickory honey hornet husky iceberg igloo indigo island ivory jaguar ' +
  'jasmine jelly jungle kayak kettle kiwi koala lagoon lantern lava lemon ' +
  'lily lime linen lion llama lobster lotus lunar lychee magnet mango maple ' +
  'marble meadow melon meteor mint mocha moose mosaic moss muffin nectar nest ' +
  'nickel noodle nutmeg oak oasis ocean olive onyx opal orbit orchid otter ' +
  'owl oyster paddle panda papaya parrot pasta peach peanut pebble pecan ' +
  'pelican penguin pepper piano pickle pine pixel planet plum polar pony ' +
  'poppy prairie pretzel puffin pumpkin quartz quill quokka rabbit radish ' +
  'rainbow raven reef ribbon river robin rocket ruby saffron sage salmon ' +
  'sandal sapphire satin scarf seal sequoia shell sierra silver sketch sloth ' +
  'snow sparrow spice spruce squid star stone summit sunset swan tango teal ' +
  'thistle thunder tiger timber toast topaz tulip tundra turtle twig umber ' +
  'valley vanilla velvet violet volcano waffle walnut walrus wasabi willow ' +
  'window winter wombat yogurt zebra zephyr zinc'
).split(' ');
