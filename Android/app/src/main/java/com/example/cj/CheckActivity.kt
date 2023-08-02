package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.net.Uri
import android.util.Log
import android.widget.ImageView
import com.bumptech.glide.Glide
import com.example.cj.databinding.ActivityCheckBinding
import com.example.cj.databinding.ActivityConveyorMainBinding

class CheckActivity : AppCompatActivity() {

    private var mBinding : ActivityCheckBinding? = null
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mBinding = ActivityCheckBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val uploadUri = intent.getParcelableExtra<Uri>("img_Uri")
        Log.d("test-uri-log", uploadUri.toString())

        if (uploadUri != null) {
            loadAndDisplayImage(uploadUri)
        } else {
            // Handle the case when uploadUri is null (error occurred during image capture)
        }

        val intent = Intent(this,StopboxMain::class.java)
        binding.cancleBottomBtn.setOnClickListener { startActivity(intent) }


    }

    private fun loadAndDisplayImage(uploadUri: Uri) {
        Glide.with(this)
            .load(uploadUri)
            .into(binding.imgView)
    }

}