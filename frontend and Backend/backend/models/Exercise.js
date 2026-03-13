import mongoose from "mongoose";

const workoutSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true
    },

    monday: {
      type: [String],
      default: []
    },

    tuesday: {
      type: [String],
      default: []
    },

    wednesday: {
      type: [String],
      default: []
    },

    thursday: {
      type: [String],
      default: []
    },

    friday: {
      type: [String],
      default: []
    },

    saturday: {
      type: [String],
      default: []
    },

    sunday: {
      type: [String],
      default: []
    }
  },
  {
    timestamps: true
  }
);

export default mongoose.model("Workout", workoutSchema);