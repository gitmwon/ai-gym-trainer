import { validationResult } from "express-validator";
import User from "../models/User.js";
import Workout from "../models/Exercise.js";
import axios from "axios";

// @desc    Setup user profile
// @route   POST /api/profile/setup
// @access  Private
export const setupProfile = async (req, res) => {
  try {
    // 1️⃣ Validate request
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        errors: errors.array(),
      });
    }

    const { fullName, age, gender, height, weight, targetWeight, fitnessGoal } =
      req.body;

    // 2️⃣ Update user
    const user = await User.findByIdAndUpdate(
      req.user._id,
      {
        fullName,
        age,
        gender,
        height,
        weight,
        targetWeight,
        fitnessGoal,
        profileCompleted: true,
      },
      { new: true, runValidators: true }
    ).select("-password");

    if (!user) {
      return res.status(404).json({
        success: false,
        message: "User not found",
      });
    }

    // 3️⃣ Call RAG service
    const ragResponse = await axios.post(
      "http://127.0.0.1:8000/generate_plan",
      { age, height, weight, targetWeight, fitnessGoal }
    );

    if (!ragResponse.data.success || !ragResponse.data.plan) {
      return res.status(500).json({
        success: false,
        message: "Failed to generate workout plan",
      });
    }

    // 4️⃣ Parse RAG plan safely
    let parsedPlan;
    try {
      parsedPlan = JSON.parse(ragResponse.data.plan);
    } catch (err) {
      console.error("Invalid JSON from RAG:", err);
      return res.status(500).json({
        success: false,
        message: "Invalid workout format received",
      });
    }

    // 5️⃣ Save workout (await so we know if it fails)
    const savedWorkout = await Workout.create({
      userId: user._id,
      ...parsedPlan,
    });

    console.log("Workout saved:", savedWorkout._id);

    // 6️⃣ Send response
    res.json({
      success: true,
      data: user,
      plan: parsedPlan, // send parsed object (better than string)
    });

  } catch (error) {
    console.error("Profile setup error:", error);
    res.status(500).json({
      success: false,
      message: "Server error during profile setup",
    });
  }
};

// @desc    Get user profile
// @route   GET /api/profile
// @access  Private
export const getProfile = async (req, res) => {
  try {
    const user = await User.findById(req.user._id).select("-password");
    const workout = await Workout.findOne({ userId: req.user._id });
    if (!user) {
      return res.status(404).json({
        success: false,
        message: "User not found",
      });
    }

    if (!workout) {
      return res.status(404).json({
        success: false,
        message: "Workout not found",
      });
    }

    res.json({
      success: true,
      data: user,
      plan: workout,
    });
  } catch (error) {
    console.error("Get profile error:", error);
    res.status(500).json({
      success: false,
      message: "Server error",
    });
  }
};
